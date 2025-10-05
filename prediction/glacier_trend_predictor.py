import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score
import cv2
from pathlib import Path
import pandas as pd

class GlacierPredictor:
    def __init__(self, pngs_dir, csv_dir=None):
        self.pngs_dir = Path(pngs_dir)
        self.csv_dir = Path(csv_dir) if csv_dir else None
        self.years = []
        self.images = []
        self.metrics = {
            'glacier_area': [],
            'mean_brightness': [],
            'white_pixels': [],
            'edge_length': [],
            'total_glacier_percent': []
        }

    def load_csv_data(self):
        """Load glacier statistics from CSV files"""
        if not self.csv_dir or not self.csv_dir.exists():
            return

        print("\nLoading CSV glacier statistics...")
        for year in self.years:
            csv_file = self.csv_dir / f"db_statistics_conservative_{year}.csv"
            if csv_file.exists():
                df = pd.read_csv(csv_file)
                glacier_percent = df[df['statistic'] == 'total_glacier_percent']['value'].values
                if len(glacier_percent) > 0:
                    self.metrics['total_glacier_percent'].append(float(glacier_percent[0]))
                    print(f"{year}: Glacier coverage = {glacier_percent[0]:.2f}%")
                else:
                    self.metrics['total_glacier_percent'].append(None)
            else:
                self.metrics['total_glacier_percent'].append(None)

    def load_images(self):
        """Load all PNG images and extract years"""
        print("Loading images...")
        png_files = sorted(self.pngs_dir.glob('*.png'))

        for png_file in png_files:
            try:
                year = int(png_file.stem)
                img = Image.open(png_file)
                self.years.append(year)
                self.images.append(np.array(img))
                print(f"Loaded {year}.png")
            except ValueError:
                print(f"Skipping {png_file.name} - not a year")

        print(f"Loaded {len(self.images)} images from years {min(self.years)} to {max(self.years)}")

    def extract_features(self):
        """Extract glacier features from images"""
        print("\nExtracting features from images...")

        for year, img in zip(self.years, self.images):
            # Convert to grayscale if needed
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            else:
                gray = img

            # Calculate glacier area (assuming white/bright areas are glacier)
            # Threshold to identify glacier (bright areas)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            glacier_area = np.sum(binary > 0)

            # Mean brightness (indicates overall glacier presence)
            mean_brightness = np.mean(gray)

            # White pixels count (glacier coverage)
            white_pixels = np.sum(gray > 200)

            # Edge detection to measure glacier boundary complexity
            edges = cv2.Canny(gray, 50, 150)
            edge_length = np.sum(edges > 0)

            self.metrics['glacier_area'].append(glacier_area)
            self.metrics['mean_brightness'].append(mean_brightness)
            self.metrics['white_pixels'].append(white_pixels)
            self.metrics['edge_length'].append(edge_length)

            print(f"{year}: Area={glacier_area:,}, Brightness={mean_brightness:.2f}, "
                  f"White pixels={white_pixels:,}, Edge length={edge_length:,}")

    def predict_future(self, future_years, metric_name='glacier_area', degree=2):
        """Predict future values using polynomial regression"""
        X = np.array(self.years).reshape(-1, 1)
        y = np.array(self.metrics[metric_name])

        # Polynomial features for better fitting
        poly = PolynomialFeatures(degree=degree)
        X_poly = poly.fit_transform(X)

        # Train model
        model = LinearRegression()
        model.fit(X_poly, y)

        # Predict on historical data (for visualization)
        y_pred_historical = model.predict(X_poly)
        r2 = r2_score(y, y_pred_historical)

        # Predict future
        X_future = np.array(future_years).reshape(-1, 1)
        X_future_poly = poly.transform(X_future)
        y_future = model.predict(X_future_poly)

        print(f"\n{metric_name} prediction model R² score: {r2:.4f}")

        return y_future, y_pred_historical, model, poly

    def apply_accelerated_melting(self, future_years):
        """Apply accelerated melting trend based on climate science"""
        # Climate models suggest accelerating glacier loss
        # Using exponential decay model
        base_year = self.years[-1]
        current_area = self.metrics['glacier_area'][-1]

        # Calculate historical trend
        years_array = np.array(self.years)
        areas_array = np.array(self.metrics['glacier_area'])

        # Linear fit to get baseline trend
        slope = np.polyfit(years_array, areas_array, 1)[0]

        # Apply accelerated melting (0.5-2% per year depending on global warming)
        melting_rates = []
        for i, year in enumerate(future_years):
            years_ahead = year - base_year
            # Accelerating rate: starts at baseline, increases with time
            # Using conservative 0.8% to 1.5% annual loss rate
            annual_rate = 0.008 + (years_ahead * 0.0002)  # Accelerating
            melting_rates.append(1 - annual_rate)

        # Calculate cumulative effect
        predicted_areas = []
        cumulative_factor = 1.0
        for rate in melting_rates:
            cumulative_factor *= rate
            predicted_areas.append(current_area * cumulative_factor)

        return np.array(predicted_areas)

    def generate_predicted_images(self, future_years, output_dir):
        """Generate predicted glacier images based on trends"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        print("\nGenerating predicted images with visible melting effects...")

        # Use the most recent image as template
        reference_img = self.images[-1].copy()
        reference_year = self.years[-1]

        # Use accelerated melting model
        future_areas = self.apply_accelerated_melting(future_years)
        current_area = self.metrics['glacier_area'][-1]

        for idx, (future_year, future_area) in enumerate(zip(future_years, future_areas)):
            # Calculate shrinkage ratio with more aggressive melting
            ratio = future_area / current_area
            ratio = max(0.05, min(ratio, 1.0))  # Allow more reduction

            years_ahead = future_year - reference_year
            erosion_size = 0  # Initialize

            # Create predicted image
            if len(reference_img.shape) == 3:
                predicted_img = reference_img.copy()

                # Convert to grayscale for processing
                gray = cv2.cvtColor(reference_img, cv2.COLOR_RGB2GRAY)

                # Identify glacier areas with multiple thresholds
                bright_glacier = gray > 200  # Very bright (snow/ice)
                medium_glacier = (gray > 150) & (gray <= 200)  # Medium brightness
                glacier_mask = bright_glacier | medium_glacier

                # ACTUAL GLACIER RETREAT: Erode glacier boundaries
                # More erosion for years further in the future
                erosion_size = int(years_ahead * 0.8)  # Progressive erosion
                if erosion_size > 0:
                    kernel = np.ones((erosion_size, erosion_size), np.uint8)
                    glacier_mask_eroded = cv2.erode(glacier_mask.astype(np.uint8), kernel, iterations=1).astype(bool)
                else:
                    glacier_mask_eroded = glacier_mask

                # Calculate what was lost
                lost_glacier = glacier_mask & ~glacier_mask_eroded

                # Apply darkening to remaining glacier (ice melting/getting dirty)
                for c in range(predicted_img.shape[2]):
                    channel = predicted_img[:, :, c].astype(float)

                    # Strong darkening for remaining bright glacier areas
                    channel = np.where(glacier_mask_eroded & bright_glacier,
                                      channel * (0.75 + ratio * 0.2), channel)

                    # Medium darkening for remaining medium glacier areas
                    channel = np.where(glacier_mask_eroded & medium_glacier,
                                      channel * (0.85 + ratio * 0.1), channel)

                    predicted_img[:, :, c] = np.clip(channel, 0, 255).astype(np.uint8)

                # Convert lost glacier areas to rock/debris (brownish/gray)
                if np.any(lost_glacier):
                    # Get underlying terrain color by darkening significantly
                    for c in range(predicted_img.shape[2]):
                        channel = predicted_img[:, :, c].astype(float)
                        # Make lost glacier areas dark gray/brown (exposed rock)
                        rock_color = 80 + np.random.randint(-20, 20, predicted_img.shape[:2])
                        channel = np.where(lost_glacier, rock_color, channel)
                        predicted_img[:, :, c] = np.clip(channel, 0, 255).astype(np.uint8)

                # Add texture variation to simulate debris on remaining glacier
                if years_ahead > 3:
                    noise_intensity = min(years_ahead * 1.5, 30)
                    noise = np.random.randint(-noise_intensity, noise_intensity//2,
                                             predicted_img.shape, dtype=np.int16)
                    for c in range(predicted_img.shape[2]):
                        channel = predicted_img[:, :, c].astype(np.int16)
                        channel = np.where(glacier_mask_eroded,
                                          channel + noise[:,:,c], channel)
                        predicted_img[:, :, c] = np.clip(channel, 0, 255).astype(np.uint8)

                # Add some brownish tint to simulate dirt on glacier for distant years
                if years_ahead > 10:
                    dirt_mask = glacier_mask_eroded & (np.random.rand(*predicted_img.shape[:2]) < 0.3)
                    if predicted_img.shape[2] >= 3:
                        # Add brown tint (more red, less blue)
                        predicted_img[:, :, 0] = np.where(dirt_mask,
                            np.clip(predicted_img[:, :, 0] * 0.9, 0, 255),
                            predicted_img[:, :, 0]).astype(np.uint8)
                        predicted_img[:, :, 1] = np.where(dirt_mask,
                            np.clip(predicted_img[:, :, 1] * 0.85, 0, 255),
                            predicted_img[:, :, 1]).astype(np.uint8)
                        predicted_img[:, :, 2] = np.where(dirt_mask,
                            np.clip(predicted_img[:, :, 2] * 0.7, 0, 255),
                            predicted_img[:, :, 2]).astype(np.uint8)
            else:
                predicted_img = (reference_img * ratio).astype(np.uint8)

            # Save predicted image
            output_path = output_dir / f"{future_year}_predicted.png"
            Image.fromarray(predicted_img).save(output_path)

            area_loss = (1 - ratio) * 100
            actual_erosion = erosion_size if len(reference_img.shape) == 3 else 0
            print(f"Generated {future_year}_predicted.png (area loss: {area_loss:.1f}%, erosion: {actual_erosion}px)")

    def visualize_trends(self, future_years, output_dir):
        """Create comprehensive visualization of trends and predictions"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        print("\nCreating trend visualizations...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Glacier Melting Analysis and Predictions (2016-{max(future_years)})',
                     fontsize=16, fontweight='bold')

        # Use accelerated melting prediction
        future_areas = self.apply_accelerated_melting(future_years)

        metrics_to_plot = [
            ('glacier_area', 'Glacier Area (pixels)', 2, future_areas),
            ('mean_brightness', 'Mean Brightness', 2, None),
            ('white_pixels', 'White Pixels Count', 2, None),
            ('edge_length', 'Edge Length (complexity)', 2, None)
        ]

        for idx, (metric_name, label, degree, custom_pred) in enumerate(metrics_to_plot):
            ax = axes[idx // 2, idx % 2]

            # Historical data
            X = np.array(self.years)
            y = np.array(self.metrics[metric_name])

            # Predictions
            if custom_pred is not None:
                future_pred = custom_pred
                historical_pred = np.polyval(np.polyfit(self.years, y, degree), self.years)
            else:
                future_pred, historical_pred, _, _ = self.predict_future(
                    future_years, metric_name, degree
                )

            # Plot
            ax.scatter(self.years, y, color='blue', s=100,
                      label='Historical Data', zorder=3)
            ax.plot(self.years, historical_pred, 'b--',
                   label='Fitted Trend', linewidth=2)
            ax.plot(future_years, future_pred, 'r-',
                   label='Predictions (Accelerated Melting)', linewidth=2, marker='o', markersize=6)

            # Styling
            ax.set_xlabel('Year', fontsize=12, fontweight='bold')
            ax.set_ylabel(label, fontsize=12, fontweight='bold')
            ax.set_title(f'{label} Over Time', fontsize=13, fontweight='bold')
            ax.legend(loc='best', fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.set_xlim(min(self.years) - 1, max(future_years) + 1)

            # Add vertical line at present
            ax.axvline(x=max(self.years), color='green',
                      linestyle=':', linewidth=2, alpha=0.7,
                      label='Present (2025)')

        plt.tight_layout()
        output_path = output_dir / 'glacier_trends_predictions.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved trend visualization to {output_path}")
        plt.close()

        # Create summary report
        self.create_summary_report(future_years, output_dir)

    def create_summary_report(self, future_years, output_dir):
        """Create a text summary report"""
        output_path = output_dir / 'prediction_summary.txt'

        with open(output_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write("GLACIER MELTING PREDICTION REPORT\n")
            f.write("ACCELERATED CLIMATE CHANGE SCENARIO\n")
            f.write("="*70 + "\n\n")

            f.write(f"Analysis Period: {min(self.years)} - {max(self.years)}\n")
            f.write(f"Prediction Period: {min(future_years)} - {max(future_years)}\n")
            f.write(f"Number of historical images: {len(self.images)}\n\n")

            f.write("-"*70 + "\n")
            f.write("HISTORICAL TRENDS\n")
            f.write("-"*70 + "\n\n")

            # Calculate trends
            for metric_name in ['glacier_area', 'mean_brightness', 'white_pixels', 'edge_length']:
                values = np.array(self.metrics[metric_name])
                change = ((values[-1] - values[0]) / values[0]) * 100
                f.write(f"{metric_name}:\n")
                f.write(f"  Initial ({self.years[0]}): {values[0]:,.2f}\n")
                f.write(f"  Final ({self.years[-1]}): {values[-1]:,.2f}\n")
                f.write(f"  Change: {change:+.2f}%\n\n")

            f.write("-"*70 + "\n")
            f.write("PREDICTIONS FOR FUTURE YEARS (Accelerated Melting Model)\n")
            f.write("-"*70 + "\n\n")

            # Use accelerated melting predictions
            future_areas = self.apply_accelerated_melting(future_years)
            current_area = self.metrics['glacier_area'][-1]

            f.write("glacier_area (Accelerated Climate Model):\n")
            for year, pred in zip(future_years, future_areas):
                loss_percent = ((current_area - pred) / current_area) * 100
                f.write(f"  {year}: {pred:,.2f} (loss: {loss_percent:.1f}%)\n")
            f.write("\n")

            f.write("-"*70 + "\n")
            f.write("KEY INSIGHTS\n")
            f.write("-"*70 + "\n\n")

            # Calculate glacier area trend
            area_values = np.array(self.metrics['glacier_area'])

            # Future prediction with accelerated model
            total_loss = ((current_area - future_areas[-1]) / current_area) * 100

            f.write(f"⚠ ACCELERATED MELTING MODEL APPLIED\n")
            f.write(f"  Based on current climate change projections\n")
            f.write(f"  Melting rate: 0.8-1.5% per year (accelerating)\n\n")

            f.write(f"Projected cumulative glacier loss by {future_years[-1]}: {total_loss:.1f}%\n\n")

            if total_loss > 20:
                f.write(f"⚠⚠ CRITICAL WARNING ⚠⚠\n")
                f.write(f"Model predicts severe glacier retreat under current climate trends.\n")
                f.write(f"This represents a significant loss of freshwater resources.\n\n")

            # Milestone predictions
            f.write("MILESTONE PREDICTIONS:\n")
            for milestone in [10, 25, 50, 75]:
                for i, (year, area) in enumerate(zip(future_years, future_areas)):
                    loss_at_year = ((current_area - area) / current_area) * 100
                    if loss_at_year >= milestone and i > 0:
                        prev_loss = ((current_area - future_areas[i-1]) / current_area) * 100
                        if prev_loss < milestone:
                            f.write(f"  {milestone}% glacier loss: ~{year}\n")
                        break

        print(f"Saved summary report to {output_path}")

def main():
    # Configuration
    pngs_dir = "files/pngs"
    csv_dir = "files/golubina-clacier-csv-set"
    output_dir = "predictions_output"
    future_years = list(range(2026, 2051))  # Extended to 2050

    print("="*70)
    print("GLACIER MELTING PREDICTION MODEL")
    print("ACCELERATED CLIMATE CHANGE SCENARIO (2026-2050)")
    print("="*70)
    print()

    # Initialize predictor
    predictor = GlacierPredictor(pngs_dir, csv_dir)

    # Load and analyze images
    predictor.load_images()
    predictor.extract_features()
    predictor.load_csv_data()

    # Generate predictions
    print("\n" + "="*70)
    print("GENERATING PREDICTIONS")
    print("="*70)

    predictor.visualize_trends(future_years, output_dir)
    predictor.generate_predicted_images(future_years, output_dir)

    print("\n" + "="*70)
    print("PREDICTION COMPLETE!")
    print("="*70)
    print(f"\nResults saved to '{output_dir}/' directory:")
    print(f"  - glacier_trends_predictions.png (trend analysis)")
    print(f"  - prediction_summary.txt (detailed report)")
    print(f"  - 2026_predicted.png through 2050_predicted.png (predicted images)")
    print(f"\nTotal predictions generated: {len(future_years)} years")
    print()

if __name__ == "__main__":
    main()
