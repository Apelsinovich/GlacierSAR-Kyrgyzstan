import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.ensemble import RandomForestRegressor
import cv2
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

class PixelBasedGlacierPredictor:
    def __init__(self, pngs_dir, csv_dir=None):
        self.pngs_dir = Path(pngs_dir)
        self.csv_dir = Path(csv_dir) if csv_dir else None
        self.years = []
        self.images = []
        self.image_shape = None
        
    def load_images(self):
        """Load all PNG images and extract years"""
        print("Loading images...")
        png_files = sorted(self.pngs_dir.glob('*.png'))
        
        for png_file in png_files:
            try:
                year = int(png_file.stem)
                img = Image.open(png_file)
                img_array = np.array(img)
                
                if self.image_shape is None:
                    self.image_shape = img_array.shape
                    print(f"Image shape: {self.image_shape}")
                
                self.years.append(year)
                self.images.append(img_array)
                print(f"Loaded {year}.png")
            except ValueError:
                print(f"Skipping {png_file.name} - not a year")
        
        self.images = np.array(self.images)  # Shape: (num_years, height, width, channels)
        self.years = np.array(self.years)
        
        print(f"\nLoaded {len(self.images)} images from years {min(self.years)} to {max(self.years)}")
        print(f"Image stack shape: {self.images.shape}")
        
    def predict_pixel_by_pixel(self, target_years, model_type='polynomial', degree=2):
        """
        Predict future images by training a model for each pixel independently
        
        Args:
            target_years: List of years to predict (e.g., [2026])
            model_type: 'linear', 'polynomial', 'ridge', or 'exponential'
            degree: Polynomial degree (if using polynomial model)
        """
        print(f"\n{'='*70}")
        print(f"PIXEL-BY-PIXEL PREDICTION")
        print(f"Model: {model_type.upper()}, Target years: {target_years}")
        print(f"{'='*70}\n")
        
        num_years = len(self.years)
        height, width = self.image_shape[:2]
        num_channels = self.image_shape[2] if len(self.image_shape) == 3 else 1
        
        # Prepare training data (years as features)
        X_train = self.years.reshape(-1, 1)
        X_predict = np.array(target_years).reshape(-1, 1)
        
        # Initialize predicted images
        predicted_images = []
        
        for target_year in target_years:
            if len(self.image_shape) == 3:
                predicted_img = np.zeros((height, width, num_channels), dtype=np.float32)
            else:
                predicted_img = np.zeros((height, width), dtype=np.float32)
            
            print(f"\nPredicting year {target_year}...")
            print("Processing channels:")
            
            # Process each channel separately
            for channel in range(num_channels):
                print(f"  Channel {channel + 1}/{num_channels}...")
                
                # Create progress bar for pixels
                total_pixels = height * width
                
                # Process in batches for efficiency
                batch_size = 1000
                
                for start_idx in tqdm(range(0, total_pixels, batch_size), 
                                     desc=f"    Pixels", 
                                     unit="batch",
                                     leave=False):
                    end_idx = min(start_idx + batch_size, total_pixels)
                    
                    # Convert flat indices to 2D coordinates
                    indices = np.arange(start_idx, end_idx)
                    rows = indices // width
                    cols = indices % width
                    
                    # Extract pixel time series for this batch
                    pixel_time_series = self.images[:, rows, cols, channel]  # Shape: (num_years, batch_size)
                    
                    # Train and predict for each pixel in batch
                    for batch_i, (row, col) in enumerate(zip(rows, cols)):
                        y_train = pixel_time_series[:, batch_i]
                        
                        # Choose model and predict
                        try:
                            if model_type == 'linear':
                                # Simple linear regression
                                model = LinearRegression()
                                model.fit(X_train, y_train)
                                prediction = model.predict([[target_year]])[0]
                                
                            elif model_type == 'polynomial':
                                # Polynomial regression
                                poly = PolynomialFeatures(degree=degree)
                                X_poly = poly.fit_transform(X_train)
                                model = Ridge(alpha=0.1)  # Use Ridge to prevent overfitting
                                model.fit(X_poly, y_train)
                                X_pred_poly = poly.transform([[target_year]])
                                prediction = model.predict(X_pred_poly)[0]
                                
                            elif model_type == 'ridge':
                                # Ridge regression with polynomial features
                                poly = PolynomialFeatures(degree=2)
                                X_poly = poly.fit_transform(X_train)
                                model = Ridge(alpha=1.0)
                                model.fit(X_poly, y_train)
                                X_pred_poly = poly.transform([[target_year]])
                                prediction = model.predict(X_pred_poly)[0]
                                
                            elif model_type == 'exponential':
                                # Exponential decay/growth model
                                # Fit: y = a * exp(b * x)
                                # Log transform: log(y) = log(a) + b * x
                                y_train_safe = np.maximum(y_train, 1)  # Avoid log(0)
                                log_y = np.log(y_train_safe)
                                model = LinearRegression()
                                model.fit(X_train, log_y)
                                log_pred = model.predict([[target_year]])[0]
                                prediction = np.exp(log_pred)
                            
                            else:
                                raise ValueError(f"Unknown model type: {model_type}")
                            
                            # Clip prediction to valid pixel range
                            prediction = np.clip(prediction, 0, 255)
                            predicted_img[row, col, channel] = prediction
                            
                        except Exception as e:
                            # If prediction fails, use mean value
                            predicted_img[row, col, channel] = np.mean(y_train)
            
            # Convert to uint8
            predicted_img = predicted_img.astype(np.uint8)
            predicted_images.append(predicted_img)
            
            print(f"  ✓ Completed prediction for {target_year}")
        
        return predicted_images
    
    def predict_with_trend_analysis(self, target_years):
        """
        Advanced prediction using trend analysis for each pixel
        Detects if pixel is melting, stable, or growing
        """
        print(f"\n{'='*70}")
        print(f"TREND-BASED PIXEL PREDICTION")
        print(f"Target years: {target_years}")
        print(f"{'='*70}\n")
        
        height, width = self.image_shape[:2]
        num_channels = self.image_shape[2] if len(self.image_shape) == 3 else 1
        
        predicted_images = []
        
        for target_year in target_years:
            print(f"\nPredicting year {target_year} with trend analysis...")
            
            if len(self.image_shape) == 3:
                predicted_img = np.zeros((height, width, num_channels), dtype=np.float32)
            else:
                predicted_img = np.zeros((height, width), dtype=np.float32)
            
            for channel in range(num_channels):
                print(f"  Channel {channel + 1}/{num_channels}...")
                
                # Extract all pixel time series for this channel
                pixel_time_series = self.images[:, :, :, channel]  # Shape: (num_years, height, width)
                
                # Calculate trends for all pixels at once
                years_diff = len(self.years)
                
                # Calculate linear trend (slope) for each pixel
                X = np.arange(years_diff).reshape(-1, 1)
                
                for row in tqdm(range(height), desc="    Rows", leave=False):
                    for col in range(width):
                        y = pixel_time_series[:, row, col]
                        
                        # Fit linear trend
                        if np.std(y) > 0.5:  # Only fit if there's variation
                            slope = np.polyfit(X.flatten(), y, 1)[0]
                            intercept = np.polyfit(X.flatten(), y, 1)[1]
                            
                            # Extrapolate to target year
                            years_ahead = target_year - self.years[-1]
                            prediction = y[-1] + slope * years_ahead
                        else:
                            # Stable pixel, use last value
                            prediction = y[-1]
                        
                        # Apply constraints based on pixel type
                        last_value = y[-1]
                        
                        # If pixel is bright (glacier), it should darken or stay same
                        if last_value > 200 and prediction > last_value:
                            prediction = last_value * 0.98  # Slight darkening
                        
                        # If pixel is dark (rock), it should stay roughly same
                        if last_value < 100:
                            prediction = last_value
                        
                        predicted_img[row, col, channel] = np.clip(prediction, 0, 255)
            
            predicted_img = predicted_img.astype(np.uint8)
            predicted_images.append(predicted_img)
            print(f"  ✓ Completed prediction for {target_year}")
        
        return predicted_images
    
    def save_predictions(self, predicted_images, target_years, output_dir, prefix=''):
        """Save predicted images"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        print(f"\n{'='*70}")
        print("SAVING PREDICTIONS")
        print(f"{'='*70}\n")
        
        for img, year in zip(predicted_images, target_years):
            filename = f"{prefix}{year}_pixel_predicted.png"
            output_path = output_dir / filename
            Image.fromarray(img).save(output_path)
            print(f"Saved: {filename}")
        
        print(f"\n✓ All predictions saved to '{output_dir}/'")
    
    def visualize_comparison(self, predicted_images, target_years, output_dir):
        """Create comparison visualization"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        print(f"\nCreating comparison visualizations...")
        
        for pred_img, year in zip(predicted_images, target_years):
            # Compare with last known image
            last_img = self.images[-1]
            last_year = self.years[-1]
            
            fig, axes = plt.subplots(1, 3, figsize=(18, 6))
            
            # Last historical image
            axes[0].imshow(last_img)
            axes[0].set_title(f'Last Known: {last_year}', fontsize=14, fontweight='bold')
            axes[0].axis('off')
            
            # Predicted image
            axes[1].imshow(pred_img)
            axes[1].set_title(f'Predicted: {year}', fontsize=14, fontweight='bold')
            axes[1].axis('off')
            
            # Difference map
            if len(last_img.shape) == 3:
                diff = np.abs(pred_img.astype(float) - last_img.astype(float))
                diff_gray = np.mean(diff, axis=2)
            else:
                diff_gray = np.abs(pred_img.astype(float) - last_img.astype(float))
            
            im = axes[2].imshow(diff_gray, cmap='hot', vmin=0, vmax=50)
            axes[2].set_title('Difference Map', fontsize=14, fontweight='bold')
            axes[2].axis('off')
            plt.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)
            
            plt.suptitle(f'Pixel-Based Glacier Prediction: {year}', 
                        fontsize=16, fontweight='bold', y=0.98)
            plt.tight_layout()
            
            output_path = output_dir / f'comparison_{year}.png'
            plt.savefig(output_path, dpi=200, bbox_inches='tight')
            plt.close()
            
            print(f"Saved comparison: comparison_{year}.png")

    def predict_autoregressive(self, target_years, model_type='polynomial', degree=2, output_dir=None):
        """
        Predict future images autoregressively - each prediction becomes training data for next

        Args:
            target_years: List of years to predict (e.g., [2026, 2027, ..., 2050])
            model_type: 'linear', 'polynomial', 'ridge'
            degree: Polynomial degree (if using polynomial model)
            output_dir: Directory to save images immediately (optional)
        """
        print(f"\n{'='*70}")
        print(f"AUTOREGRESSIVE PIXEL-BY-PIXEL PREDICTION")
        print(f"Model: {model_type.upper()}, Years: {min(target_years)}-{max(target_years)}")
        print(f"{'='*70}\n")

        height, width = self.image_shape[:2]
        num_channels = self.image_shape[2] if len(self.image_shape) == 3 else 1

        # Start with historical data
        current_years = self.years.copy()
        current_images = self.images.copy()

        predicted_images = []

        # Create output directory if specified
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)

        for target_year in target_years:
            print(f"\nPredicting year {target_year} (using {len(current_years)} historical years)...")

            if len(self.image_shape) == 3:
                predicted_img = np.zeros((height, width, num_channels), dtype=np.float32)
            else:
                predicted_img = np.zeros((height, width), dtype=np.float32)

            # Prepare training data
            X_train = np.array(current_years).reshape(-1, 1)

            print("Processing channels:")

            # Process each channel separately
            for channel in range(num_channels):
                print(f"  Channel {channel + 1}/{num_channels}...")

                total_pixels = height * width
                batch_size = 1000

                for start_idx in tqdm(range(0, total_pixels, batch_size),
                                     desc=f"    Pixels",
                                     unit="batch",
                                     leave=False):
                    end_idx = min(start_idx + batch_size, total_pixels)

                    # Convert flat indices to 2D coordinates
                    indices = np.arange(start_idx, end_idx)
                    rows = indices // width
                    cols = indices % width

                    # Extract pixel time series for this batch
                    pixel_time_series = current_images[:, rows, cols, channel]

                    # Train and predict for each pixel in batch
                    for batch_i, (row, col) in enumerate(zip(rows, cols)):
                        y_train = pixel_time_series[:, batch_i]

                        # Choose model and predict
                        try:
                            if model_type == 'linear':
                                model = LinearRegression()
                                model.fit(X_train, y_train)
                                prediction = model.predict([[target_year]])[0]

                            elif model_type == 'polynomial':
                                poly = PolynomialFeatures(degree=degree)
                                X_poly = poly.fit_transform(X_train)
                                model = Ridge(alpha=0.5)  # Increased regularization for stability
                                model.fit(X_poly, y_train)
                                X_pred_poly = poly.transform([[target_year]])
                                prediction = model.predict(X_pred_poly)[0]

                            elif model_type == 'ridge':
                                poly = PolynomialFeatures(degree=2)
                                X_poly = poly.fit_transform(X_train)
                                model = Ridge(alpha=1.0)
                                model.fit(X_poly, y_train)
                                X_pred_poly = poly.transform([[target_year]])
                                prediction = model.predict(X_pred_poly)[0]

                            else:
                                raise ValueError(f"Unknown model type: {model_type}")

                            # Clip prediction to valid pixel range
                            prediction = np.clip(prediction, 0, 255)
                            predicted_img[row, col, channel] = prediction

                        except Exception as e:
                            # If prediction fails, use last value
                            predicted_img[row, col, channel] = y_train[-1]

            # Convert to uint8
            predicted_img = predicted_img.astype(np.uint8)
            predicted_images.append(predicted_img)

            # SAVE IMMEDIATELY after predicting each year
            if output_dir:
                filename = f"auto_poly2_{target_year}_pixel_predicted.png"
                output_path = output_dir / filename
                Image.fromarray(predicted_img).save(output_path)
                print(f"  ✓ Saved: {filename}")

            # Add prediction to training data for next iteration (AUTOREGRESSIVE)
            current_years = np.append(current_years, target_year)
            current_images = np.append(current_images, [predicted_img], axis=0)

            print(f"  ✓ Completed prediction for {target_year}")
            print(f"  ✓ Added to training data (now have {len(current_years)} years)")

        return predicted_images

    def predict_autoregressive_with_constraints(self, target_years, output_dir=None):
        """
        Autoregressive prediction with physical constraints (glacier can only melt/darken)
        """
        print(f"\n{'='*70}")
        print(f"CONSTRAINED AUTOREGRESSIVE PREDICTION")
        print(f"Years: {min(target_years)}-{max(target_years)}")
        print(f"{'='*70}\n")

        height, width = self.image_shape[:2]
        num_channels = self.image_shape[2] if len(self.image_shape) == 3 else 1

        # Start with historical data
        current_years = self.years.copy()
        current_images = self.images.copy()

        predicted_images = []

        # Create output directory if specified
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)

        for target_year in target_years:
            print(f"\nPredicting year {target_year} (using {len(current_years)} years)...")

            if len(self.image_shape) == 3:
                predicted_img = np.zeros((height, width, num_channels), dtype=np.float32)
            else:
                predicted_img = np.zeros((height, width), dtype=np.float32)

            for channel in range(num_channels):
                print(f"  Channel {channel + 1}/{num_channels}...")

                # Extract all pixel time series for this channel
                pixel_time_series = current_images[:, :, :, channel]

                X = np.arange(len(current_years)).reshape(-1, 1)

                for row in tqdm(range(height), desc="    Rows", leave=False):
                    for col in range(width):
                        y = pixel_time_series[:, row, col]

                        # Fit linear trend
                        if np.std(y) > 0.5:
                            slope = np.polyfit(X.flatten(), y, 1)[0]

                            # Extrapolate
                            prediction = y[-1] + slope
                        else:
                            prediction = y[-1]

                        # Apply physical constraints
                        last_value = y[-1]

                        # Glacier pixels (bright) should only darken or stay same
                        if last_value > 200:
                            prediction = min(prediction, last_value * 0.995)  # Max 0.5% darkening per year

                        # Medium brightness pixels can darken slowly
                        elif last_value > 150:
                            prediction = min(prediction, last_value * 0.998)

                        # Dark pixels (rock) stay relatively stable
                        elif last_value < 100:
                            prediction = last_value * 0.999  # Very slow change

                        predicted_img[row, col, channel] = np.clip(prediction, 0, 255)

            predicted_img = predicted_img.astype(np.uint8)
            predicted_images.append(predicted_img)

            # SAVE IMMEDIATELY after predicting each year
            if output_dir:
                filename = f"constrained_{target_year}_pixel_predicted.png"
                output_path = output_dir / filename
                Image.fromarray(predicted_img).save(output_path)
                print(f"  ✓ Saved: {filename}")

            # Add to training data (AUTOREGRESSIVE)
            current_years = np.append(current_years, target_year)
            current_images = np.append(current_images, [predicted_img], axis=0)

            print(f"  ✓ Completed prediction for {target_year}")

        return predicted_images

def main():
    # Configuration
    pngs_dir = "files/pngs"
    csv_dir = "files/golubina-clacier-csv-set"
    output_dir = "pixel_predictions_autoregressive"
    target_years = list(range(2026, 2035))  # Autoregressive predictions 2026-2050

    print("="*70)
    print("AUTOREGRESSIVE PIXEL-BASED GLACIER PREDICTION MODEL")
    print("Predicting 2026-2050 sequentially (each year uses previous predictions)")
    print("="*70)
    print()
    
    # Initialize predictor
    predictor = PixelBasedGlacierPredictor(pngs_dir, csv_dir)
    
    # Load images
    predictor.load_images()
    
    print(f"\nHistorical data: {len(predictor.years)} images")
    print(f"Years: {list(predictor.years)}")
    print(f"Total pixels to predict: {predictor.image_shape[0] * predictor.image_shape[1]:,}")
    print(f"Total years to predict: {len(target_years)} years ({min(target_years)}-{max(target_years)})")

    # Method 1: Autoregressive Polynomial Regression
    print("\n" + "="*70)
    print("METHOD 1: AUTOREGRESSIVE POLYNOMIAL REGRESSION (Degree 2)")
    print("="*70)
    predicted_imgs_auto_poly = predictor.predict_autoregressive(
        target_years,
        model_type='polynomial', 
        degree=2,
        output_dir=output_dir  # Pass output_dir to save images immediately
    )
    # No need to call save_predictions again since images are already saved

    # Create comparison for select years
    select_years = [2026, 2030, 2035, 2040, 2045, 2050]
    select_indices = [target_years.index(y) for y in select_years if y in target_years]
    select_images = [predicted_imgs_auto_poly[i] for i in select_indices]
    predictor.visualize_comparison(select_images, select_years, output_dir)

    # Method 2: Constrained Autoregressive (More Realistic)
    print("\n" + "="*70)
    print("METHOD 2: CONSTRAINED AUTOREGRESSIVE (Physical Constraints)")
    print("="*70)
    predicted_imgs_constrained = predictor.predict_autoregressive_with_constraints(
        target_years,
        output_dir=output_dir  # Pass output_dir to save images immediately
    )
    # No need to call save_predictions again since images are already saved

    # Create timeline visualization
    print("\nCreating timeline visualization...")
    create_timeline_visualization(
        predictor.images[-1],
        predictor.years[-1],
        predicted_imgs_auto_poly,
        target_years,
        output_dir
    )

    print("\n" + "="*70)
    print("AUTOREGRESSIVE PREDICTION COMPLETE!")
    print("="*70)
    print(f"\nResults saved to '{output_dir}/' directory:")
    print(f"  - auto_poly2_YYYY_pixel_predicted.png (25 images, 2026-2050)")
    print(f"  - constrained_YYYY_pixel_predicted.png (25 images, 2026-2050)")
    print(f"  - comparison_YYYY.png (Selected years)")
    print(f"  - timeline.png (Overview of glacier evolution)")
    print()
    print("✓ Each year was predicted using ALL previous years as training data!")
    print("✓ The model learns from its own predictions (autoregressive)")
    print()

def create_timeline_visualization(last_historical_img, last_year, predicted_images, years, output_dir):
    """Create a timeline showing glacier evolution"""
    output_dir = Path(output_dir)

    # Select years to display (every 5 years)
    display_years = [last_year] + [y for y in years if (y - 2025) % 5 == 0]
    display_images = [last_historical_img] + [predicted_images[years.index(y)] for y in display_years[1:]]

    num_images = len(display_images)
    cols = 5
    rows = (num_images + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(20, 4 * rows))
    axes = axes.flatten() if num_images > 1 else [axes]

    for idx, (img, year) in enumerate(zip(display_images, display_years)):
        axes[idx].imshow(img)
        if year == last_year:
            axes[idx].set_title(f'{year}\n(Historical)', fontsize=12, fontweight='bold', color='blue')
        else:
            axes[idx].set_title(f'{year}\n(Predicted)', fontsize=12, fontweight='bold', color='red')
        axes[idx].axis('off')

    # Hide unused subplots
    for idx in range(num_images, len(axes)):
        axes[idx].axis('off')

    plt.suptitle('Glacier Evolution Timeline (Autoregressive Prediction)',
                 fontsize=16, fontweight='bold')
    plt.tight_layout()

    output_path = output_dir / 'timeline.png'
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()

    print(f"Saved timeline: timeline.png")

if __name__ == "__main__":
    main()
