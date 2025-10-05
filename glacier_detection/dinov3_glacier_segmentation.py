print("Script starting...")
import matplotlib
matplotlib.use('Agg')

import numpy as np
import torch
from PIL import Image
import matplotlib.pyplot as plt
import os

from transformers import AutoImageProcessor, AutoModel

from skimage.transform import resize
from skimage.color import rgb2hsv
from skimage.filters import sobel, threshold_otsu
from skimage.morphology import remove_small_objects, binary_opening, binary_closing, disk
from skimage.segmentation import slic, find_boundaries, random_walker

from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture

# Reproducibility
np.random.seed(42)
torch.manual_seed(42)

print("[1/9] Loading DINOv3 model and processor...")
processor = AutoImageProcessor.from_pretrained("facebook/dinov3-vitl16-pretrain-sat493m")
model = AutoModel.from_pretrained("facebook/dinov3-vitl16-pretrain-sat493m")

# Device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()
print(f"    Using device: {device}")

# --- 2. Load Image ---
image_path = 'img.png'
print(f"[2/9] Loading image: {os.path.abspath(image_path)}")
image = Image.open(image_path).convert("RGB")
img_np = np.array(image).astype(np.float32) / 255.0
H_img, W_img = image.height, image.width
print(f"    Image size: {W_img}x{H_img}")

# --- 3. Preprocess and Forward ---
print("[3/9] Running DINOv3 forward pass...")
inputs = processor(images=image, return_tensors="pt")
inputs = {k: v.to(device) for k, v in inputs.items()}
with torch.no_grad():
    outputs = model(**inputs)

# --- 4. Derive patch grid and CLS–Patch similarity map ---
patch_size = getattr(getattr(model.config, 'vision_config', model.config), 'patch_size', 16)
H_proc = int(inputs['pixel_values'].shape[2])
W_proc = int(inputs['pixel_values'].shape[3])
h = H_proc // patch_size
w = W_proc // patch_size
num_patch_tokens = h * w
print(f"[4/9] Patch grid: {w}x{h} (patch_size={patch_size})")

last_hidden = outputs.last_hidden_state
cls = last_hidden[0, 0, :]
patches = last_hidden[0, 1:1+num_patch_tokens, :]
cls_n = cls / (cls.norm(p=2) + 1e-6)
patches_n = patches / (patches.norm(p=2, dim=1, keepdim=True) + 1e-6)
fmap_1d = (patches_n @ cls_n)
fmap_2d = fmap_1d.reshape(h, w)

# Resize saliency to image size and normalize
saliency_map_resized = resize(fmap_2d.detach().cpu().numpy(), (H_img, W_img), preserve_range=True)
sal = saliency_map_resized
sal = (sal - sal.min()) / (sal.max() - sal.min() + 1e-6)

# --- 5. Patch features (DINO + color/texture/saliency) ---
print("[5/9] Building features (PCA on DINO + color/texture/saliency)...")
patch_tokens_last = last_hidden[0, 1:1+num_patch_tokens, :].detach().cpu().numpy()
# Ensure n_components <= min(n_samples, n_features) for PCA
n_samples, n_features = patch_tokens_last.shape[0], patch_tokens_last.shape[1]
n_components = min(64, n_features, n_samples)
pca = PCA(n_components=n_components, random_state=42)
dino_feats = pca.fit_transform(patch_tokens_last)
img_small = resize(img_np, (h, w, 3), preserve_range=True, anti_aliasing=True)
img_hsv = rgb2hsv(img_small)
R, G, B = img_small[..., 0], img_small[..., 1], img_small[..., 2]
S = img_hsv[..., 1]
V = img_hsv[..., 2]
blue_ratio = B / (R + G + B + 1e-6)
gray_small = 0.299 * R + 0.587 * G + 0.114 * B
tex = sobel(gray_small)
sal_patch = fmap_2d.detach().cpu().numpy()
sal_patch = (sal_patch - sal_patch.min()) / (sal_patch.max() - sal_patch.min() + 1e-6)
aux_features = []
for comp in [R, G, B, S, V, blue_ratio, tex, sal_patch]:
    comp_n = (comp - comp.min()) / (comp.max() - comp.min() + 1e-6)
    aux_features.append(comp_n)
aux_feats = np.stack(aux_features, axis=-1).reshape(-1, len(aux_features))
feats = np.concatenate([dino_feats, aux_feats], axis=1)
print(f"    Feature matrix: {feats.shape}")

# --- 6. Unsupervised clustering to get glacier probabilities ---
print("[6/9] Fitting GaussianMixture (2 components) and mapping snow cluster...")
gmm = GaussianMixture(n_components=2, covariance_type='full', max_iter=200, random_state=42)
gmm.fit(feats)
resp = gmm.predict_proba(feats)
V_f = V.reshape(-1)
S_f = S.reshape(-1)
Bf = blue_ratio.reshape(-1)
Sal_f = sal_patch.reshape(-1)
scores = []
for k in range(2):
    w_k = resp[:, k]
    w_k = w_k / (w_k.sum() + 1e-6)
    score_k = 0.45 * (w_k @ V_f) + 0.25 * (w_k @ (1 - S_f)) + 0.20 * (w_k @ Bf) + 0.10 * (w_k @ Sal_f)
    scores.append(score_k)
snow_idx = int(np.argmax(scores))
probs_patch = resp[:, snow_idx]
probs_2d = probs_patch.reshape(h, w)
print(f"    Snow component index: {snow_idx}")

# --- 7. Upscale and refine with superpixels + Random Walker ---
print("[7/9] Refining with SLIC superpixels and Random Walker...")
prob_img = resize(probs_2d, (H_img, W_img), order=1, preserve_range=True, anti_aliasing=True)
prob_img = np.clip(prob_img, 0.0, 1.0).astype(np.float32)

# Apply SLIC superpixels for spatial coherence
n_segments = max(200, (H_img * W_img) // 1500)
segments = slic(img_np, n_segments=n_segments, compactness=10, sigma=1, start_label=0, channel_axis=-1)
prob_sp = prob_img.copy()
for seg_id in np.unique(segments):
    mask_sp = (segments == seg_id)
    mean_p = prob_img[mask_sp].mean()
    prob_sp[mask_sp] = mean_p
prob_img = prob_sp  # This is a 2D array with shape (H_img, W_img)

# Create seed labels for Random Walker
labels_seed = np.full((H_img, W_img), -1, dtype=np.int32)
labels_seed[prob_img > 0.8] = 1  # Snow/glacier seeds
labels_seed[prob_img < 0.2] = 0  # Non-snow/glacier seeds

# Force seed creation even if thresholds didn't catch anything
flat = prob_img.flatten()  # Use flatten() instead of reshape(-1)
N = flat.size
k = max(100, int(0.005 * N))  # Increased seed count
order = np.argsort(flat)
labels_seed = np.full((H_img, W_img), -1, dtype=np.int32)
labels_seed.flatten()[order[:k]] = 0  # Use flatten() for consistency
labels_seed.flatten()[order[-k:]] = 1

# Ensure seeds are well distributed
if np.count_nonzero(labels_seed == 1) < 50 or np.count_nonzero(labels_seed == 0) < 50:
    # Simple thresholding as fallback if Random Walker can't run
    mask_simple = prob_img > 0.5
    prob_img = mask_simple.astype(np.float32)
else:
    # Run Random Walker algorithm with adjusted parameters
    try:
        probs_rw = random_walker(img_np, labels_seed, beta=10, mode='bf', tol=1e-3,
                             return_full_prob=True, channel_axis=-1)
        prob_img = probs_rw[1].astype(np.float32)
    except Exception as e:
        print(f"    Random Walker failed: {e}, using simple thresholding")
        # Simple thresholding as fallback
        mask_simple = prob_img > 0.5
        prob_img = mask_simple.astype(np.float32)


# --- 8. Morphological cleanup and border extraction ---
print("[8/9] Thresholding and morphology...")
try:
    # Make sure prob_img is flattened if needed
    if len(prob_img.shape) != 2:
        prob_img = prob_img.reshape(H_img, W_img)
    th = threshold_otsu(prob_img)
except Exception as e:
    print(f"    Otsu thresholding failed: {e}, using default threshold 0.5")
    th = 0.5

# Create binary mask and ensure it has the correct shape
if len(prob_img.shape) != 2:
    prob_img = prob_img.reshape(H_img, W_img)
mask_bin = prob_img > th

# Apply morphological operations
area_thresh = int(0.002 * mask_bin.size)
mask_bin = remove_small_objects(mask_bin, min_size=area_thresh)
mask_bin = binary_opening(mask_bin, footprint=disk(2))
mask_bin = binary_closing(mask_bin, footprint=disk(2))

# Find boundaries
edges = find_boundaries(mask_bin, mode='thick')

print(f"    Otsu threshold: {th:.3f}")
print(f"    Glacier area fraction: {mask_bin.mean()*100:.2f}%")

# --- 9. Visualize and Save Results ---
print("[9/9] Saving outputs...")
fig, axes = plt.subplots(2, 3, figsize=(18, 12))

# Original
axes[0, 0].imshow(image)
axes[0, 0].set_title("Original Image")
axes[0, 0].axis('off')

# Saliency overlay
axes[0, 1].imshow(image)
axes[0, 1].imshow(sal, cmap='jet', alpha=0.45)
axes[0, 1].set_title("DINOv3 CLS–Patch Similarity")
axes[0, 1].axis('off')

# Seeds from probabilities (for visualization only)
pos_seed = probs_2d > 0.8
neg_seed = probs_2d < 0.2
seed_vis = np.zeros((h, w, 3), dtype=np.float32)
seed_vis[pos_seed] = [0.1, 0.8, 0.1]  # green
seed_vis[neg_seed] = [0.8, 0.1, 0.1]  # red
axes[0, 2].imshow(resize(seed_vis, (H_img, W_img), order=0, preserve_range=True))
axes[0, 2].set_title("Seeds (green=snow, red=non-snow)")
axes[0, 2].axis('off')

# Patch-level probability map (resized)
axes[1, 0].imshow(resize(probs_2d, (H_img, W_img), preserve_range=True), cmap='viridis', vmin=0, vmax=1)
axes[1, 0].set_title("Glacier Probability (patch->pixel)")
axes[1, 0].axis('off')

# Refined probability
axes[1, 1].imshow(prob_img, cmap='viridis', vmin=0, vmax=1)
axes[1, 1].set_title("Refined Probability (SLIC + RandomWalker)")
axes[1, 1].axis('off')

# Final mask + borders
axes[1, 2].imshow(image)
border_overlay = np.zeros((H_img, W_img, 4), dtype=np.float32)
border_overlay[..., 0] = edges.astype(np.float32)  # red borders
border_overlay[..., 3] = edges.astype(np.float32) * 0.9
axes[1, 2].imshow(mask_bin, cmap='Blues', alpha=0.45)
axes[1, 2].imshow(border_overlay)
axes[1, 2].set_title("Glacier Mask + Borders")
axes[1, 2].axis('off')

plt.tight_layout()
plt.savefig('dinov3_glacier_segment.png', dpi=200)

# Save artifacts
from PIL import Image as _Image
_Image.fromarray((mask_bin.astype(np.uint8) * 255)).save('glacier_mask.png')
_Image.fromarray((np.clip(prob_img, 0, 1) * 255).astype(np.uint8)).save('glacier_probability.png')
_Image.fromarray((sal * 255).astype(np.uint8)).save('saliency_map.png')

# Save borders as a colored PNG overlay with transparency
edges_rgba = np.zeros((H_img, W_img, 4), dtype=np.uint8)
# Make sure edges has the correct shape
edges = edges.reshape(H_img, W_img)  # Fix potential shape issues
edges_rgba[..., 0] = (edges.astype(np.uint8) * 255)  # red
edges_rgba[..., 3] = (edges.astype(np.uint8) * 255)  # alpha
_Image.fromarray(edges_rgba, mode='RGBA').save('glacier_edges.png')

for name in [
    'dinov3_glacier_segment.png',
    'glacier_mask.png',
    'glacier_probability.png',
    'saliency_map.png',
    'glacier_edges.png',
]:
    print(f"    Saved {name} -> {os.path.abspath(name)}")

print("Done.")
