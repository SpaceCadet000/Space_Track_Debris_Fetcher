Here’s a complete, production-ready `README.md` you can directly upload with your script.

---

# 🚀 Space-Track Debris TLE Downloader

Download space debris and satellite **TLE (Two-Line Element)** data directly from Space-Track using a fully interactive Python script.

This tool allows you to filter orbital objects by multiple criteria and export them in formats suitable for analysis, simulation, or tracking.

---

## 📌 Features

* 🔐 Secure login (via environment variables or prompt)
* 🧠 Interactive CLI (no need to remember API syntax)
* 🎯 Advanced filtering:

  * Object type (Debris, Rocket Body, Payload, etc.)
  * Orbital regime (LEO, MEO, GEO, HEO)
  * Decayed objects
  * Radar Cross Section (RCS)
  * Epoch recency (last 30/90/365 days, etc.)
  * Country of origin
* 📦 Multiple output formats:

  * TLE (2-line)
  * 3LE (with object name)
  * CSV
  * JSON
* ⚡ Smart downloading:

  * Attempts bulk download first
  * Falls back to batched queries if needed
* 📝 Metadata saved alongside data

---

## 📂 File Included

*

---

## ⚙️ Requirements

* Python 3.8+
* Internet connection
* Space-Track account (free)

### Install dependencies

```bash
pip install requests
```

---

## 🔑 Space-Track Account Setup

1. Go to Space-Track
2. Register for a free account
3. Wait for approval (can take a few hours)

---

## ▶️ Usage

Run the script:

```bash
python space_track_downloader.py
```

---

## 🔐 Authentication Options

### Option 1 — Environment Variables (Recommended)

```bash
export SPACETRACK_USER="your_email"
export SPACETRACK_PASS="your_password"
```

### Option 2 — Interactive Prompt

The script will ask for:

* Username (email)
* Password (hidden input)

---

## 🧭 How It Works

### 1. Interactive Configuration

The script asks you to configure:

* Object types (Debris, Rocket Bodies, etc.)
* Include/exclude decayed objects
* Orbital regime:

  * LEO (<2000 km)
  * MEO (2000–35,586 km)
  * GEO (~1436 min period)
  * HEO (eccentricity > 0.25)
* Radar Cross Section (size of object)
* Epoch freshness (recent TLEs)
* Country filter
* Output format

---

### 2. Query Construction

Based on your inputs, the script builds a Space-Track API query like:

```
/class/gp/OBJECT_TYPE/DEBRIS/PERIGEE/<2000/EPOCH/>now-30/format/tle
```

---

### 3. Data Download Strategy

* ✅ First tries a **single bulk request**
* 🔁 If that fails:

  * Splits into **NORAD ID batches**
  * Downloads incrementally
  * Stops early when no more data is found

---

### 4. Output Files

After execution, two files are created:

#### 📄 Data file

```
spacetrack_debris_YYYYMMDD_HHMMSS.tle
```

(or `.csv`, `.json` depending on format)

#### 📄 Metadata file

```
spacetrack_debris_YYYYMMDD_HHMMSS_meta.json
```

Includes:

* Query parameters
* Object count
* Timestamp
* Filters used

---

## 📊 Output Formats Explained

| Format | Description                              |
| ------ | ---------------------------------------- |
| `tle`  | Standard 2-line format (SGP4 compatible) |
| `3le`  | Includes object name (3-line format)     |
| `csv`  | Full dataset, ideal for analysis         |
| `json` | Structured data for programming          |

---

## 📈 Example Output (TLE)

```
1 25544U 98067A   24001.12345678  .00002182  00000-0  45000-4 0  9991
2 25544  51.6441 123.4567 0001234  45.6789 314.5678 15.50000000 12345
```

---

## ⚠️ Notes & Best Practices

* ⏱️ Respect API rate limits (script includes delays)
* 📡 Large queries may take time
* 🔄 Use filters to reduce dataset size
* 🔐 Never hardcode credentials in public repos

---

## 🐛 Troubleshooting

### ❌ Login Failed

* Check credentials
* Ensure account is approved

### ❌ No Data Returned

* Your filters may be too strict
* Try broader settings

### ❌ Timeout Errors

* Script automatically switches to batch mode
* Just wait — it will continue

---

## 🧪 Example Use Cases

* Space debris tracking
* Orbital simulations
* Satellite collision analysis
* Academic research
* Space situational awareness (SSA)

---

## 📜 License

MIT License (or add your preferred license)

---

## 🙌 Credits

* Data provided by Space-Track
* Script built using Python + requests

---

## ⭐ Contributing

Pull requests welcome!
If you find bugs or want improvements, open an issue.

---

If you want, I can also:

* Add badges (GitHub, license, Python version)
* Create a `.gitignore`
* Write a proper release description for GitHub 🚀
