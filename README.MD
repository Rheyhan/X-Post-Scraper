# X (formerly Twitter) Post Scraper

A Python-based scraper to extract posts from X (formerly Twitter) based on specific search criteria, using Selenium with an undetected ChromeDriver for web automation.

Originally built for personal research (e.g., #Terimakasihjokowi during Prabowo's inauguration in late 2024). If ur interested in collaborating or have questions, feel free to reach out!

## Features
- Filtered search with full query composition (keywords, accounts, hashtags, min counts, replies/links) (see [X Advanced Search](https://x.com/search-advanced))
- Date-range crawling with automatic day stepback when no posts are found
- Duplicate protection across resumed sessions
- Auto-save and resume from savepoints
- CSV and JSON export options

## Example Output
Example data can be found in [Process](Process).

| User | Date | post_text | quotedPost_text | Reply_count | Repost_count | Like_count | View_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| @PolitisiTidurr | 2026-01-15-19:30:18 | Ini bukan lagi program "Makan Bergizi Gratis" (MBG), tapi "Malapetaka Beracun Gratis". Angka 21.254 korban bukan sekadar statistik, itu adalah nyawa anak-anak yang dijadikan kelinci percobaan kebijakan populis yang dipaksakan tanpa kesiapan sanitasi dan pengawasan logistik. |  | 0 | 0 | 0 | 86 |

## Requirements
- Python 3.9+
- Google Chrome installed

## Setup
1. Clone the repository:

    ```bash
    git clone
    ```

2. Edit credentials at [Credentials/twitter.json](Credentials/twitter.json) with the format:

	```json
	{
	  "username": "your_username",
	  "password": "your_password",
	  "email": "your_email"
	}
	```

3. Install dependencies:

	```bash
    pip install -r requirements.txt
	```

## Usage
The main notebook is [SRC.IPYNB](SRC.IPYNB). It contains:
- The `twitterScrapper` class
- Examples of filter configuration
- Example `session.start(...)` calls

Quick flow:
1. Open the notebook
2. Update filters
3. Run the scraping cell

## Output
By default, outputs are stored in:
- [Process](Process) for current runs
- Savepoints under the selected process directory
- Final CSV/JSON on completion

## Project Structure (high level)
- [SRC.IPYNB](SRC.IPYNB): main implementation + usage
- [Debug.ipynb](Debug.ipynb): debugging and testing, useful if you want to modify the code and test it
- [Requirements.txt](Requirements.txt): dependencies
- [Credentials](Credentials): Credentials storage
- [Process](Process): runtime outputs and savepoints
- [LEGACY](LEGACY): old versions (deprecated)

## Pipeline of the LEGACY code (Deprecated)
![alt text](image.png)

## Notes
- X may trigger “suspicious login attempt” and require email verification.
- If scraping detection occurs, the scraper can auto-save and wait before continuing.

## Disclaimer
This tool is intended for educational and research purposes only. Ensure compliance with X’s terms of service and privacy policies when using this scraper. The author is not responsible for any misuse of this tool.