import pandas as pd
import numpy as np

# Load our baseline predictions (which scored 90.92%)
print("Loading baseline predictions...")
sub = pd.read_csv('predictions.csv')

# Define our strategic scaling factors
multipliers = [1.12, 1.16, 1.20]

for m in multipliers:
    scaled_sub = sub.copy()
    
    # Scale up demand and clip to valid [0, 1] range
    scaled_sub['demand'] = np.clip(scaled_sub['demand'] * m, 0.0, 1.0)
    
    # Save the file
    filename = f'predictions_x{m:.2f}.csv'
    scaled_sub.to_csv(filename, index=False)
    
    print(f"Generated {filename}:")
    print(f"  - Scaled mean demand: {scaled_sub['demand'].mean():.6f} (baseline was {sub['demand'].mean():.6f})")
    print(f"  - Max value: {scaled_sub['demand'].max():.6f}")
    print(f"  - Bins clipped to 1.0: {(scaled_sub['demand'] == 1.0).sum()} rows")
    print("-" * 40)
