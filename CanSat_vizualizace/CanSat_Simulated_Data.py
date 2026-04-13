import random

def generate_lora_log(filename="test_lora_log.txt", num_lines=1000):
    # Starting conditions (simulating a CanSat deployed at 1000m)
    temp = 13.8
    hum = 55.2
    press = 900.1
    alt = 1002.3
    lat = 49.7520
    lon = 16.6850
    rssi = -92
    snr = 6.5

    with open(filename, "w", encoding="utf-8") as f:
        for _ in range(num_lines):
            # 1. Format and write the current state to the file using letter prefixes
            # A=TEMP, B=HUM, C=ALT, D=PRESS, E=LAT, F=LON, R=RSSI, S=SNR
            line = (f"A{temp:.1f};B{hum:.1f};D{press:.1f};"
                    f"C{alt:.1f};E{lat:.4f};F{lon:.4f}|"
                    f"R{rssi}|S{snr:.1f}\n")
            f.write(line)

            # 2. Mutate the variables slightly for the next line (Random Walk)
            temp += random.uniform(-0.2, 0.3)      # Temp slowly rises as it gets lower
            hum += random.uniform(-0.5, 0.5)       # Humidity fluctuates
            
            # Simulate descent
            alt -= random.uniform(0.5, 2.0)        # Drops 0.5 to 2.0 meters per tick
            if alt < 0: 
                alt = 0.0
            
            press += random.uniform(0.05, 0.2)     # Pressure increases as altitude drops
            
            # GPS drift (wind blowing it slightly)
            lat += random.uniform(-0.00005, 0.0001)
            lon += random.uniform(-0.00005, 0.0001)
            
            # Radio link quality fluctuates
            rssi += random.randint(-2, 2)
            if rssi > -40: rssi = -40              # Max signal cap
            if rssi < -120: rssi = -120            # Min signal cap
            
            snr += random.uniform(-0.5, 0.5)

    print(f"Successfully generated {num_lines} lines in {filename}")

if __name__ == "__main__":
    generate_lora_log("test_lora_log.txt", 1000)