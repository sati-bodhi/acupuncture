# Classical Acupuncture Information System

## Overview

This is a comprehensive Classical Acupuncture Information System that combines traditional Chinese medicine principles with modern data management and web technologies. The system provides practitioners with tools for diagnosis, treatment planning, and accessing detailed information about acupuncture points, meridians, and classical treatment methodologies.

## Features

### Core Functionality

- **Acupoint & Meridian Database**: Complete database of acupuncture points and meridians with Chinese, English, and transliterated names
- **Diagnostic Tools**: Multiple diagnostic frameworks including:
  - Eight Principles (八綱辨證) - Qi, Blood, Yin, Yang diagnosis
  - Six Channels & Six Qi (六經與六氣) - External pathogen diagnosis
  - Five Elements (五行) - Acute and chronic conditions
  - Extraordinary Vessels (奇經八脈) - Energy distribution
  - Horary Clock (子午流注) - Time-based treatment and jet lag adjustment
  - Luo Vessels (絡脈) - Longitudinal and transverse vessel treatments
  - Group Luo (組絡) - Pain and hemiplegia treatments

### Database Structure

The SQLite database (`acu.db`) contains:
- Acupoint locations and descriptions
- Meridian routes and relationships
- Five Shu points (五輸穴)
- Mu-Shu points (募俞穴)
- Luo-connecting points
- Extraordinary vessel meeting points
- Classical text references from sources like 黃帝內經 and 奇經八脈考

## Technology Stack

- **Backend**: Python 3.10 with Django web framework
- **Database**: SQLite3
- **Frontend**: Bootstrap 5, HTML5
- **Additional Libraries**:
  - `hanlp` - Chinese natural language processing
  - `pypinyin` - Chinese character transliteration
  - `opencc` - Traditional/Simplified Chinese conversion
  - `networkx` - Graph visualization for energy cycles
  - `matplotlib` - Medical diagrams
  - `skyfield` - Solar time calculations
  - `pytz`/`zoneinfo` - Timezone handling

## Installation

### Prerequisites

- Python 3.10+
- Anaconda or pip package manager

### Setup Steps

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up the database:
```python
cd acupuncture
python build_db.py
```

4. Run Django migrations:
```bash
cd webapp
python manage.py makemigrations
python manage.py migrate
```

5. Start the development server:
```bash
python manage.py runserver
```

6. Access the application at `http://localhost:8000`

## Project Structure

```
├── acupuncture/          # Core acupuncture logic and database
│   ├── build_db.py       # Database initialization
│   ├── element.py        # Five Elements theory implementation
│   ├── meridian.py       # Meridian and phenomena calculations
│   ├── extraordinary.py  # Extraordinary vessels logic
│   ├── complement.py     # Luo vessels and complementary treatments
│   ├── diagnostics.py    # Diagnostic algorithms
│   └── acu.db           # SQLite database
│
├── webapp/              # Django web application
│   ├── data_assist/     # Main Django app
│   │   ├── views.py     # View controllers
│   │   ├── urls.py      # URL routing
│   │   └── templates/   # HTML templates
│   └── manage.py        # Django management script
```

## Usage

### Query System
- Search for acupuncture points by Chinese name, Pinyin, or international code
- Browse meridian information with classical route descriptions
- View point locations, indications, and special attributes

### Diagnostic Tools

1. **Eight Principles**: Input pulse characteristics and generate treatment prescriptions
2. **Six Channels**: Select environmental pathogens for preventive or treatment protocols
3. **Five Elements**: Seasonal organ energy assessment with acute/chronic differentiation
4. **Horary Clock**: Calculate optimal treatment times and jet lag adjustments
5. **Extraordinary Vessels**: Balance energy distribution through master points
6. **Luo Vessels**: Treat specific symptoms through longitudinal and transverse vessels

### Treatment Planning
- Automated prescription generation based on classical formulas
- Point combinations with tonification/sedation indicators
- Seasonal and temporal considerations
- Integration of multiple diagnostic frameworks

## Key Algorithms

- **Seasonal Lord Calculation**: Determines the governing organ based on solar terms
- **Energy Cycle Balancing**: Uses Five Element generation and control cycles
- **Horary Flow**: Calculates meridian activation times based on solar position
- **Luo Vessel Symptom Matching**: Pattern recognition for vessel-specific symptoms
- **Group Luo Algorithm**: Determines point combinations for pain patterns

## Data Sources

The system integrates information from:
- Wikipedia acupuncture point lists
- A+醫學百科 (Medical Encyclopedia)
- Classical texts (黃帝內經, 奇經八脈考)
- Pialoux's Classical Acupuncture methodology
- WHO International Standard codes

## Notes for Practitioners

- The system follows Classical Acupuncture principles as taught in the French-Vietnamese tradition
- International Standard (IS) codes are used primarily, with PRC standard codes maintained for reference
- Seasonal calculations use astronomical solar terms (節氣)
- All prescriptions should be validated by qualified practitioners

## Development

### Adding New Features
1. Extend the database schema in `build_db.py`
2. Add logic modules to the `acupuncture` package
3. Create Django views and templates
4. Update URL routing

### Testing
Run Django tests:
```bash
python manage.py test
```

## License

This project is intended for educational and clinical reference purposes. Please respect the intellectual property of classical texts and modern interpretations.

## Acknowledgments

- Classical Chinese Medicine texts and their translators
- Dr. Jacques Pialoux for the systematic approach to Classical Acupuncture
- The open-source community for essential libraries and tools

## Contact

For questions or contributions, please contact the development team through the repository.

---

*Note: This system is a reference tool and should not replace professional medical training or clinical judgment.*
