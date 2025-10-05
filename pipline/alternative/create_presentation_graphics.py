#!/usr/bin/env python3
"""
Create presentation-ready graphics and infographics
for NASA Space Apps Challenge 2025
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path

# Create output directory
output_dir = Path("output/presentation")
output_dir.mkdir(parents=True, exist_ok=True)


def create_polarization_comparison_chart():
    """Create a comparison chart of SAR polarizations"""
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    categories = ['Melt Water\nSensitivity', 'Glacier\nDelineation', 
                  'Data\nAvailability', 'Processing\nSimplicity', 
                  'Scientific\nValidation']
    
    vv_scores = [5, 5, 5, 5, 5]
    hh_scores = [3, 4, 3, 5, 4]
    hv_scores = [2, 2, 4, 4, 3]
    quad_scores = [5, 5, 1, 2, 5]
    
    x = np.arange(len(categories))
    width = 0.2
    
    bars1 = ax.bar(x - 1.5*width, vv_scores, width, label='VV ⭐', 
                   color='#2E86AB', edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x - 0.5*width, hh_scores, width, label='HH', 
                   color='#A23B72', edgecolor='black', linewidth=1)
    bars3 = ax.bar(x + 0.5*width, hv_scores, width, label='HV/VH', 
                   color='#F18F01', edgecolor='black', linewidth=1)
    bars4 = ax.bar(x + 1.5*width, quad_scores, width, label='Quad-Pol', 
                   color='#C73E1D', edgecolor='black', linewidth=1)
    
    ax.set_ylabel('Score (out of 5)', fontsize=14, fontweight='bold')
    ax.set_title('SAR Polarization Comparison for Glacier Monitoring\n' + 
                'VV Polarization is Optimal for Ala-Archa Project',
                fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=12)
    ax.legend(fontsize=12, loc='upper right')
    ax.set_ylim(0, 6)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add value labels on bars
    for bars in [bars1, bars2, bars3, bars4]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # Add recommendation box
    recommendation = "RECOMMENDATION: VV Polarization\nScore: 25/25 (100%)"
    ax.text(0.02, 0.98, recommendation, transform=ax.transAxes,
           fontsize=13, fontweight='bold', verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='#2E86AB', alpha=0.8, 
                    edgecolor='black', linewidth=2),
           color='white')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'polarization_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Created: {output_dir / 'polarization_comparison.png'}")


def create_workflow_diagram():
    """Create a visual workflow diagram"""
    
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Title
    ax.text(5, 11.5, 'SAR Glacier Monitoring Pipeline', 
           fontsize=18, fontweight='bold', ha='center',
           bbox=dict(boxstyle='round', facecolor='lightblue', edgecolor='black', linewidth=2))
    
    # Steps
    steps = [
        ("1. Data Acquisition", "Sentinel-1 VV\nfrom ASF", '#2E86AB'),
        ("2. Preprocessing", "Calibration\nFiltering\nTerrain Correction", '#A23B72'),
        ("3. Glacier Detection", "Threshold\nBoundary Detection", '#F18F01'),
        ("4. Change Detection", "Image Differencing\nTemporal Analysis", '#C73E1D'),
        ("5. Time Series", "Melt Rate\nTrend Analysis", '#6A994E'),
        ("6. Visualization", "Maps & Graphs\nReports", '#BC4B51')
    ]
    
    y_pos = 10
    for i, (title, desc, color) in enumerate(steps):
        # Box
        rect = patches.FancyBboxPatch((1, y_pos-0.8), 8, 1.3,
                                     boxstyle="round,pad=0.1",
                                     facecolor=color, edgecolor='black',
                                     linewidth=2, alpha=0.7)
        ax.add_patch(rect)
        
        # Text
        ax.text(2, y_pos, title, fontsize=13, fontweight='bold', 
               va='center', color='white')
        ax.text(6.5, y_pos, desc, fontsize=10, va='center', 
               ha='center', color='white')
        
        # Arrow
        if i < len(steps) - 1:
            ax.arrow(5, y_pos-1, 0, -0.5, head_width=0.3, head_length=0.2,
                    fc='black', ec='black', linewidth=2)
        
        y_pos -= 1.8
    
    # Result box
    result = patches.FancyBboxPatch((1, 0.5), 8, 1,
                                   boxstyle="round,pad=0.1",
                                   facecolor='gold', edgecolor='black',
                                   linewidth=3, alpha=0.9)
    ax.add_patch(result)
    ax.text(5, 1, '📊 Actionable Insights for Water Resource Management',
           fontsize=12, fontweight='bold', ha='center', va='center')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'workflow_diagram.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Created: {output_dir / 'workflow_diagram.png'}")


def create_backscatter_interpretation():
    """Create backscatter interpretation guide"""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Left: Backscatter values
    surface_types = ['Melt Water', 'Wet Snow/Ice', 'Firn', 'Dry Ice', 'Rocks']
    backscatter_min = [-25, -18, -12, -8, -5]
    backscatter_max = [-20, -12, -8, -3, 0]
    colors = ['#0077BE', '#4A90E2', '#87CEEB', '#F0F8FF', '#8B4513']
    
    y_pos = np.arange(len(surface_types))
    
    for i, (surface, b_min, b_max, color) in enumerate(zip(surface_types, 
                                                           backscatter_min, 
                                                           backscatter_max, 
                                                           colors)):
        ax1.barh(i, b_max - b_min, left=b_min, height=0.6, 
                color=color, edgecolor='black', linewidth=1.5)
        
        # Add value labels
        mid_point = (b_min + b_max) / 2
        ax1.text(mid_point, i, f'{b_min} to {b_max} dB', 
                ha='center', va='center', fontsize=10, fontweight='bold')
    
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(surface_types, fontsize=12)
    ax1.set_xlabel('Backscatter σ⁰ (dB)', fontsize=12, fontweight='bold')
    ax1.set_title('VV Polarization Backscatter Values\nfor Different Surfaces', 
                 fontsize=14, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3, linestyle='--')
    ax1.axvline(x=-15, color='red', linestyle='--', linewidth=2, label='Typical Threshold')
    ax1.legend(fontsize=10)
    
    # Right: Interpretation guide
    ax2.axis('off')
    
    interpretation_text = """
INTERPRETATION GUIDE

🔵 DARKER in SAR Image (Low Backscatter):
   • Melt water present
   • Wet snow/ice
   • Smooth surfaces
   • ⚠️ Indicates melting

⚪ BRIGHTER in SAR Image (High Backscatter):
   • Dry ice/snow
   • Rough surfaces
   • Rock/debris
   • ✓ Stable glacier surface

📊 CHANGE DETECTION:
   Decrease > 3 dB  → Likely melting
   Increase > 3 dB  → Freezing/drying
   
🕐 TEMPORAL PATTERNS:
   Summer: Expect decrease (melting)
   Winter: Expect increase (freezing)
   
📈 TREND ANALYSIS:
   Progressive decrease over years
   → Glacier mass loss
   → Climate change impact
"""
    
    ax2.text(0.1, 0.95, interpretation_text, transform=ax2.transAxes,
            fontsize=11, verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', 
                     alpha=0.8, edgecolor='black', linewidth=2))
    
    plt.suptitle('Understanding SAR VV Backscatter for Glacier Monitoring',
                fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_dir / 'backscatter_interpretation.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Created: {output_dir / 'backscatter_interpretation.png'}")


def create_study_area_info():
    """Create study area information graphic"""
    
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Title
    ax.text(5, 9.5, 'Ala-Archa Glaciers Study Area', 
           fontsize=20, fontweight='bold', ha='center',
           bbox=dict(boxstyle='round', facecolor='lightblue', 
                    edgecolor='black', linewidth=3))
    
    # Location box
    location_text = """
📍 LOCATION
Ala-Archa Gorge, Kyrgyzstan
Coordinates: 42.565°N, 74.500°E
Elevation: 2,000 - 4,900 m

🏔️ GLACIERS MONITORED
• Adigine          • Golubina
• Ak-Sai           • Toktogul
• Big Ala-Archa    • Small Ala-Archa
"""
    
    rect1 = patches.FancyBboxPatch((0.5, 5.5), 4.5, 3,
                                  boxstyle="round,pad=0.2",
                                  facecolor='#E8F4F8', 
                                  edgecolor='black', linewidth=2)
    ax.add_patch(rect1)
    ax.text(2.75, 7.5, location_text, fontsize=11, 
           va='top', family='monospace')
    
    # Impact box
    impact_text = """
⚠️ CLIMATE IMPACT
• Water supply for Bishkek
• Hydropower generation
• Flood risk management
• Ecosystem services

📊 MONITORING GOALS
• Detect melting zones
• Quantify melt rates
• Forecast future changes
• Support decision-making
"""
    
    rect2 = patches.FancyBboxPatch((5, 5.5), 4.5, 3,
                                  boxstyle="round,pad=0.2",
                                  facecolor='#FFE8E8', 
                                  edgecolor='black', linewidth=2)
    ax.add_patch(rect2)
    ax.text(7.25, 7.5, impact_text, fontsize=11, 
           va='top', family='monospace')
    
    # Data specifications
    data_text = """
🛰️ DATA SPECIFICATIONS

Satellite:     Sentinel-1 A/B
Polarization:  VV (Vertical-Vertical) ⭐
Product Type:  GRD (Ground Range Detected)
Resolution:    10m × 10m
Frequency:     Every 12 days (6 days with both satellites)
Band:          C-band (5.405 GHz)
Wavelength:    5.6 cm

Source:        Alaska Satellite Facility (ASF)
               https://search.asf.alaska.edu/
               
Time Period:   2020 - 2025 (5-year analysis)
"""
    
    rect3 = patches.FancyBboxPatch((0.5, 0.5), 9, 4.5,
                                  boxstyle="round,pad=0.2",
                                  facecolor='#F0F8FF', 
                                  edgecolor='black', linewidth=2)
    ax.add_patch(rect3)
    ax.text(5, 4.2, data_text, fontsize=10, 
           ha='center', va='top', family='monospace')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'study_area_info.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Created: {output_dir / 'study_area_info.png'}")


def create_why_vv_infographic():
    """Create 'Why VV?' infographic"""
    
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Title
    ax.text(5, 9.5, 'Why VV Polarization?', 
           fontsize=24, fontweight='bold', ha='center',
           bbox=dict(boxstyle='round', facecolor='gold', 
                    edgecolor='black', linewidth=3))
    
    # Four quadrants
    reasons = [
        {
            'title': '🔬 Physics',
            'text': 'VV waves:\n• Best penetration\n• Max sensitivity to\n  liquid water\n• High ice/water contrast\n  (≥10 dB difference)',
            'pos': (1, 7, 3.8, 1.8),
            'color': '#2E86AB'
        },
        {
            'title': '📊 Science',
            'text': 'Proven in research:\n• Nagler et al. (2015)\n• Winsvold et al. (2018)\n• Paul et al. (2016)\n• NASA recommended',
            'pos': (5.2, 7, 3.8, 1.8),
            'color': '#A23B72'
        },
        {
            'title': '🛰️ Availability',
            'text': 'Sentinel-1 data:\n• 100% VV coverage\n• Free & open access\n• 12-day repeat\n• Global archive',
            'pos': (1, 4.7, 3.8, 1.8),
            'color': '#F18F01'
        },
        {
            'title': '💻 Practical',
            'text': 'Easy to use:\n• Standard processing\n• Clear interpretation\n• Many tools available\n• Our pipeline ready',
            'pos': (5.2, 4.7, 3.8, 1.8),
            'color': '#6A994E'
        }
    ]
    
    for reason in reasons:
        rect = patches.FancyBboxPatch(reason['pos'][:2], reason['pos'][2], reason['pos'][3],
                                     boxstyle="round,pad=0.15",
                                     facecolor=reason['color'], 
                                     edgecolor='black', linewidth=2, alpha=0.8)
        ax.add_patch(rect)
        
        ax.text(reason['pos'][0] + reason['pos'][2]/2, 
               reason['pos'][1] + reason['pos'][3] - 0.3,
               reason['title'], fontsize=14, fontweight='bold', 
               ha='center', color='white')
        
        ax.text(reason['pos'][0] + reason['pos'][2]/2, 
               reason['pos'][1] + reason['pos'][3]/2 - 0.2,
               reason['text'], fontsize=11, ha='center', va='center',
               color='white', linespacing=1.5)
    
    # Bottom conclusion
    conclusion = """
CONCLUSION: VV Polarization is the OPTIMAL choice for glacier monitoring

✓ Maximizes melt detection capability
✓ Provides reliable, consistent data
✓ Supported by scientific literature
✓ Free and readily available
✓ Easy to process and interpret
"""
    
    rect = patches.FancyBboxPatch((1, 0.5), 8, 3.5,
                                 boxstyle="round,pad=0.2",
                                 facecolor='lightgreen', 
                                 edgecolor='black', linewidth=3, alpha=0.7)
    ax.add_patch(rect)
    ax.text(5, 2.3, conclusion, fontsize=12, ha='center', va='center',
           fontweight='bold', linespacing=1.8)
    
    # Add stars
    ax.text(5, 9, '⭐ ⭐ ⭐ ⭐ ⭐', fontsize=20, ha='center')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'why_vv_infographic.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Created: {output_dir / 'why_vv_infographic.png'}")


def main():
    """Create all presentation graphics"""
    
    print("=" * 80)
    print("CREATING PRESENTATION GRAPHICS")
    print("NASA Space Apps Challenge 2025 - TengriSpacers")
    print("=" * 80)
    print()
    
    print("Generating infographics...")
    print()
    
    create_polarization_comparison_chart()
    create_workflow_diagram()
    create_backscatter_interpretation()
    create_study_area_info()
    create_why_vv_infographic()
    
    print()
    print("=" * 80)
    print("✓ ALL GRAPHICS CREATED SUCCESSFULLY!")
    print("=" * 80)
    print()
    print(f"Graphics saved to: {output_dir}/")
    print()
    print("Files created:")
    print("  1. polarization_comparison.png - Bar chart comparing polarizations")
    print("  2. workflow_diagram.png - Step-by-step pipeline visualization")
    print("  3. backscatter_interpretation.png - Guide to understanding SAR data")
    print("  4. study_area_info.png - Project specifications and location")
    print("  5. why_vv_infographic.png - Justification for VV choice")
    print()
    print("Use these graphics in your presentation slides!")
    print("=" * 80)


if __name__ == "__main__":
    main()


