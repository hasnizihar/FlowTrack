# YOLOv9-Traffic-Analysis-Pipeline

**Computer-Vision-Based Traffic Flow Analysis** using **YOLOv9** + **DeepSORT**

A complete Python pipeline that processes traffic surveillance video to automatically detect, classify, and track vehicles — then extracts traffic engineering parameters (flow rates, speed distributions, vehicle composition) and generates publication-quality charts.


## 📂 Project Structure

```
Traffic-Analysis-Pipeline/
│
├── scripts/                              # Pipeline scripts (run in order)
│   ├── config.py                         # Central configuration — all paths & parameters
│   ├── step1_extract_frame.py            # Extract a still frame from the video
│   ├── step2_mark_gcps.py                # Interactive GCP / ROI / detection line marker
│   ├── step3_homography.py               # Compute homography matrix (perspective correction)
│   ├── step4_annotate_frame.py           # Create annotated benchmark image for report
│   ├── step5_detect_track.py             # YOLOv9 + DeepSORT detection & tracking
│   ├── step6_speed.py                    # Speed estimation from tracked positions
│   ├── step7_traffic_params.py           # Flow rates, composition, speed statistics
│   ├── step8_plots.py                    # Generate all publication-quality charts
│   └── run_all.py                        # Master runner (steps 5 → 8 sequentially)
│
├── models/                               # YOLO model weights (not tracked — see Setup)
│   └── yolov9t.pt                        # YOLOv9 Tiny (download separately)
│
├── data/                                 # Site measurement data (GCPs, lane widths)
│   ├── GPS Location.txt                  # (Example) GPS coordinates of GCPs
│   └── Lane Widths.txt                   # (Example) Lane width measurements
│
├── Raw video/                            # Source video (not tracked — too large)
│   └── traffic_video.mp4                 # Your traffic recording
│
├── output/                               # All generated outputs
│   ├── still_frame.jpg                   # Extracted calibration frame
│   ├── still_frame_annotated.jpg         # Annotated benchmark image
│   ├── homography_matrix.npy             # Camera calibration matrix
│   ├── gcps_pixel.json                   # GCP pixel coordinates
│   ├── gcps_world.json                   # GCP real-world coordinates (metres)
│   ├── road_area.json                    # Road area polygon (ROI)
│   ├── detection_line.json               # Vehicle counting line
│   ├── vehicle_counts.csv                # Raw vehicle detection records
│   ├── vehicle_speeds.csv                # Speed per tracked vehicle
│   ├── flow_1min.csv / 5min / 10min      # Flow rate data at different intervals
│   ├── composition.csv                   # Vehicle type breakdown
│   ├── speed_stats.csv                   # Speed statistics by type & lane
│   ├── flow_plot_*.png                   # Flow rate time-series charts
│   ├── composition_pie.png               # Overall composition donut chart
│   ├── composition_bar.png               # Per-lane composition bar chart
│   ├── speed_hist_*.png                  # Speed distribution per vehicle type
│   ├── speed_histograms.png              # Combined speed panel
│   └── speed_boxplot.png                 # Speed comparison box plot
│
├── Bin/                                  # Archived/old files (gitignored)
├── .gitignore
├── requirements.txt                      # Python dependencies
├── LICENSE                               # MIT License
└── README.md                             # This file
```

---

## ⚙️ Setup

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/Traffic-Analysis-Pipeline.git
cd Traffic-Analysis-Pipeline
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download YOLO Model Weights

The model weights (`.pt` files) are **not included** in the repository due to their size. Download them into the `models/` directory:

| Model | Size | Use Case | Download |
|---|---|---|---|
| **yolov9t.pt** (recommended) | ~5 MB | CPU — fast inference | [Ultralytics YOLOv9](https://docs.ultralytics.com/models/yolov9/) |
| yolov9c.pt (optional) | ~52 MB | GPU — higher accuracy | [Ultralytics YOLOv9](https://docs.ultralytics.com/models/yolov9/) |

```bash
# Using Ultralytics CLI:
yolo export model=yolov9t.pt
# Or download manually and place in models/
```

### 5. Place Your Video

Put your traffic recording at:
```
Raw video/traffic_video.mp4
```

---

## 🚀 Usage

### Phase 1: Calibration (Interactive — Run Once)

These steps require manual interaction (clicking on the image):

```bash
# Step 1: Extract a still frame from the video
python scripts/step1_extract_frame.py

# Step 2: Mark Ground Control Points, Road Area & Detection Line
python scripts/step2_mark_gcps.py
#   → Press [1] for GCP mode, [2] for Road Area, [3] for Detection Line
#   → LEFT-CLICK to add points, RIGHT-CLICK to undo
#   → Press ENTER to save and quit

# Step 3: Edit output/gcps_world.json with real-world coordinates (metres)
#   → Or run process_gps.py from Bin/ to compute from GPS data

# Step 4: Compute the homography (perspective correction) matrix
python scripts/step3_homography.py

# Step 5: Create the annotated benchmark image (for your report)
python scripts/step4_annotate_frame.py
```

### Phase 2: Full Analysis (Automated)

```bash
# Run the entire pipeline (detection → speed → params → plots)
python scripts/run_all.py

# Skip annotated video output (much faster):
python scripts/run_all.py --no-video

# Limit number of frames (for testing):
python scripts/step5_detect_track.py --frames 1000
```

### Or Run Steps Individually

```bash
python scripts/step5_detect_track.py        # Detection & tracking (~30-60 min on CPU)
python scripts/step6_speed.py               # Speed estimation
python scripts/step7_traffic_params.py      # Traffic parameter extraction
python scripts/step8_plots.py               # Generate all charts
```

---

## 📊 Output Files

| File | Description |
|---|---|
| `vehicle_counts.csv` | Timestamped record of every vehicle crossing the detection line |
| `vehicle_speeds.csv` | Estimated speed (km/h) per tracked vehicle |
| `flow_1min.csv` / `5min` / `10min` | Flow rates (veh/hr) at different time intervals |
| `composition.csv` | Vehicle type count & percentage by lane |
| `speed_stats.csv` | Speed statistics (mean, std, quartiles) by type & lane |
| `flow_plot_*.png` | Flow rate vs. time line charts |
| `composition_pie.png` | Overall vehicle composition donut chart |
| `composition_bar.png` | Per-lane vehicle composition bar chart |
| `speed_hist_*.png` | Individual speed distribution histograms per type |
| `speed_histograms.png` | Combined speed distribution panel |
| `speed_boxplot.png` | Comparative speed box plot across vehicle types |
| `annotated_output.mp4` | Full video with bounding boxes & labels (7+ GB) |

---

## 🚗 Vehicle Classification

The pipeline classifies **7 Sri Lankan vehicle types** using YOLOv9 COCO detection + bounding-box geometry refinement:

| Vehicle Type | Detection Method |
|---|---|
| **Motorcycle** | COCO class 3 (direct) |
| **Three-Wheeler** | COCO class 2 (Car) → refined by small area + square aspect ratio |
| **Car** | COCO class 2 (default) |
| **Van** | COCO class 2 (Car) → refined by wide aspect ratio |
| **Light Goods Vehicle** | COCO class 7 (Truck) → refined by small area |
| **Bus** | COCO class 5 (direct) |
| **Heavy Goods Vehicle** | COCO class 7 (Truck) → refined by large area |

---

## 🛠 Technology Stack

| Component | Technology |
|---|---|
| **Object Detection** | YOLOv9 (Ultralytics) — superior architecture to YOLOv8 |
| **Object Tracking** | DeepSORT — multi-object tracking across frames |
| **Video Processing** | OpenCV — frame extraction, homography, annotation |
| **Data Analysis** | Pandas + NumPy — data wrangling & statistics |
| **Visualization** | Matplotlib — publication-quality charts |
| **Perspective Correction** | OpenCV Homography — pixel → real-world coordinate mapping |

---

## 📋 Pipeline Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Step 1-4   │    │    Step 5    │    │   Step 6-7   │    │    Step 8    │
│ Calibration  │───→│  Detection   │───→│  Analysis    │───→│    Plots    │
│ (one-time)   │    │ & Tracking   │    │ & Statistics │    │ & Charts    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
     │                    │                    │                    │
 still_frame.jpg     vehicle_counts.csv   flow_*.csv          flow_plot_*.png
 homography.npy      track_history.pkl    composition.csv     composition_*.png
 gcps_*.json         annotated_output.mp4 speed_stats.csv     speed_*.png
 detection_line.json vehicle_speeds.csv
```

---

## 📝 Report Structure

Use the generated output data and plots for your report:

1. **Introduction** — Context, site rationale, objectives
2. **Study Site** — Site description, lane configuration, recording conditions
3. **Methodology** — Annotated benchmark image, homography calibration, YOLOv9 + DeepSORT pipeline
4. **Results** — Flow rate plots (1/5/10 min), composition charts, speed histograms & statistics
5. **Discussion** — Peak analysis, speed differences by class, limitations, improvement suggestions

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
