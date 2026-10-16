# Igneous Rock Study Lab

A beginner-friendly, image-based geology quiz built with Python and Streamlit. Students can open the hosted website in a browser; they do not need Python installed.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```
5. Your browser should open automatically.

## Share it online

Recommended starting point: Streamlit Community Cloud. Put this folder in a GitHub repository, then create an app at https://share.streamlit.io and select `app.py` as the entrypoint. Follow Streamlit's current deployment instructions.

If your photos are large, check the repository and hosting limits. Compress copies of photos for web use and keep original images backed up elsewhere.

## Add specimens

Edit `specimens.json`. Add another object inside the `"specimens"` array. Use the same structure as an example specimen and give each specimen a unique `id`.

Image paths are relative to the project folder. For example:
- `images/minerals/olivine_ppl_01.jpg`
- `images/minerals/olivine_xpl_01.jpg`
- `images/hand_samples/gabbro_01.jpg`
- `images/thin_sections/basalt_01.jpg`

Create the relevant folders if needed, and use simple filenames without unusual characters. The image files themselves are not included in this starter project.

### Specimen types

- `"type": "mineral"` — use `mineral` and `image_pairs`. Each pair has `ppl` and `xpl` image paths. Add multiple pairs to randomize which view is shown.
- `"type": "hand_sample"` — use `image`, `rock_name`, and `answers.qap`, `answers.accessory_minerals`.
- `"type": "thin_section_rock"` with `"texture": "aphanitic"` — uses phenocryst, matrix and porosity answers.
- `"type": "thin_section_rock"` with `"texture": "phaneritic"` — uses QAP, normalized QAP, rock type, accessory percentages, and full rock name.

### Important composition convention

For the aphanitic quiz, the example schema expects phenocryst and matrix mineral percentages to be **percentages of the whole rock**, not percentages within just the phenocryst or matrix fraction. The total phenocryst and total matrix fields are also percentages of the whole rock. Make sure your answer keys follow the convention taught in your course.

For the phaneritic quiz, the first QAP estimate is checked against the supplied target values. The normalized estimate must sum to 100%. Feedback uses a default tolerance of ±5 percentage points. You can change this in `app.py` if your course uses a different tolerance.

## What to customize next

- Replace the example answer keys with your own specimen data.
- Add your images to the paths referenced in the JSON.
- Add more rock/mineral options to the per-specimen option lists.
- Consider adding topic tags (e.g. aphanitic, phaneritic, porphyritic, vesicular) if you want to filter quizzes by texture.

## Notes

This is a starter implementation. It does not save individual student scores or accounts. The app randomizes specimen order for each round, and the mineral quiz randomizes the PPL/XPL pair shown for each mineral. If a quiz type has fewer specimens than the requested question count, the app uses each available specimen once rather than repeating specimens.
