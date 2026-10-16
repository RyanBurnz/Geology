import json
import random
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "specimens.json"
IMAGE_DIR = BASE_DIR / "images"

st.set_page_config(page_title="Igneous Rock Study Lab", page_icon="🪨", layout="wide")

DEFAULT_MINERALS = [
    "Quartz", "K-feldspar", "Plagioclase", "Biotite", "Hornblende",
    "Olivine", "Pyroxene", "Muscovite", "Amphibole", "Magnetite",
    "Apatite", "Garnet", "Other / unsure"
]

def load_specimens():
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("specimens", [])

def image_path(relative_path):
    if not relative_path:
        return None
    p = (BASE_DIR / relative_path).resolve()
    try:
        p.relative_to(BASE_DIR.resolve())
    except ValueError:
        return None
    return p if p.exists() and p.is_file() else None

def show_image(relative_path, caption=None, width=None):
    p = image_path(relative_path)
    if p:
        st.image(str(p), caption=caption, width=width, use_container_width=(width is None))
    else:
        st.info(f"Image not added yet: `{relative_path or 'no path supplied'}`")

def reset_quiz():
    for key in list(st.session_state.keys()):
        if key.startswith("quiz_") or key.startswith("answer_"):
            del st.session_state[key]

def start_quiz(specimens, quiz_type, count):
    candidates = [s for s in specimens if s.get("type") == quiz_type]
    if not candidates:
        st.error("There are no specimens for this quiz type yet. Add some to specimens.json.")
        return
    random.shuffle(candidates)
    selected = candidates[:min(count, len(candidates))]
    st.session_state.quiz_items = selected
    st.session_state.quiz_index = 0
    st.session_state.quiz_type = quiz_type
    st.session_state.quiz_started = True
    st.session_state.quiz_run_id = st.session_state.get("quiz_run_id", 0) + 1
    st.rerun()

def get_answer(item, key, default=None):
    return item.get("answers", {}).get(key, default)

def feedback_numeric(label, entered, target, tolerance=5, suffix="%"):
    if target is None:
        st.info("No answer key entered for this field yet.")
        return
    delta = abs(float(entered) - float(target))
    if delta <= tolerance:
        st.success(f"{label}: close enough — your answer was {entered:g}{suffix}; target is {target:g}{suffix}.")
    else:
        st.warning(f"{label}: your answer was {entered:g}{suffix}; target is {target:g}{suffix} (difference {delta:g}{suffix}).")

def mineral_options(specimens):
    found = set(DEFAULT_MINERALS)
    for s in specimens:
        found.update(s.get("mineral_options", []))
        for key in ("mineral", "rock_name", "rock_type"):
            if s.get(key):
                found.add(s[key])
        for m in s.get("answers", {}).get("phenocrysts", []):
            found.add(m)
        for m in s.get("answers", {}).get("matrix_minerals", []):
            found.add(m)
        for m in s.get("answers", {}).get("accessory_minerals", []):
            found.add(m)
    return sorted(found, key=str.casefold)

def question_header(item, idx, total):
    st.progress((idx + 1) / total)
    st.subheader(f"Question {idx + 1} of {total}")
    st.caption(item.get("label", item.get("id", "Specimen")))

def reveal_button(item, keys):
    if st.button("Reveal answer", key=f"reveal_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}"):
        for key in keys:
            value = item.get("answers", {}).get(key)
            if value is not None:
                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
        if item.get("explanation"):
            st.info(item["explanation"])

def next_question():
    if st.session_state.quiz_index + 1 >= len(st.session_state.quiz_items):
        st.session_state.quiz_started = False
        st.session_state.quiz_finished = True
    else:
        st.session_state.quiz_index += 1
    st.rerun()

def render_mineral(item, all_minerals):
    variants = item.get("image_pairs", [])
    if variants:
        pair = random.choice(variants) if st.session_state.get("active_pair_key") != f"{st.session_state.quiz_run_id}-{st.session_state.quiz_index}" else st.session_state.get("active_pair")
        if st.session_state.get("active_pair_key") != f"{st.session_state.quiz_run_id}-{st.session_state.quiz_index}":
            st.session_state.active_pair = pair
            st.session_state.active_pair_key = f"{st.session_state.quiz_run_id}-{st.session_state.quiz_index}"
        pair = st.session_state.active_pair
        cols = st.columns(2)
        with cols[0]:
            show_image(pair.get("ppl"), "PPL")
        with cols[1]:
            show_image(pair.get("xpl"), "XPL")
    else:
        show_image(item.get("image"), "Thin section")
    st.write("Identify the mineral shown.")
    options = [x for x in all_minerals if x != "Other / unsure"]
    choice = st.selectbox("Mineral", options, key=f"mineral_choice_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}")
    if st.button("Check answer", key=f"check_min_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}"):
        target = item.get("mineral")
        if target and choice.casefold() == target.casefold():
            st.success("Correct!")
        else:
            st.error("Not quite. Try again — attempts are unlimited.")
    reveal_button(item, ["mineral"])
    if st.button("Next specimen", key=f"next_min_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}"):
        next_question()

def render_hand_sample(item, minerals):
    show_image(item.get("image"), "Hand sample")
    answers = item.get("answers", {})
    st.markdown("#### Step 1 — Estimate QAP composition")
    st.caption("Estimate the relative percentages of Quartz, K-feldspar and Plagioclase. Use your best estimate; the three numbers do not have to sum to 100 for this first pass.")
    qap = {}
    cols = st.columns(3)
    for col, m in zip(cols, ["quartz", "k_feldspar", "plagioclase"]):
        with col:
            qap[m] = st.number_input(m.replace("_", " ").title() + " (%)", min_value=0, max_value=100, value=0, step=5, key=f"hand_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}_{m}")
    if st.button("Check QAP estimates", key=f"hand_qap_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}"):
        target = answers.get("qap", {})
        for m, val in qap.items():
            feedback_numeric(m.replace("_", " ").title(), val, target.get(m))
    if st.button("Reveal QAP answer", key=f"hand_reveal_qap_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}"):
        st.write("**QAP target:**", answers.get("qap", "Not supplied"))
    st.divider()
    st.markdown("#### Step 2 — Accessory minerals")
    accessory_options = item.get("accessory_options", minerals)
    selected = st.multiselect("Select the most common accessory mineral(s)", accessory_options, key=f"hand_access_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}")
    if st.button("Check accessory minerals", key=f"hand_check_access_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}"):
        target = set(answers.get("accessory_minerals", []))
        if set(selected) == target:
            st.success("Correct!")
        else:
            st.warning(f"Not quite. You selected {len(set(selected) & target)} of {len(target)} target mineral(s). Try again.")
    st.divider()
    st.markdown("#### Step 3 — Name the rock")
    rock_choices = item.get("rock_options", sorted({s.get("rock_name") for s in st.session_state.all_specimens if s.get("rock_name")}))
    rock = st.selectbox("Rock name", rock_choices, key=f"hand_rock_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}")
    if st.button("Check rock name", key=f"hand_check_rock_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}"):
        if rock.casefold() == str(item.get("rock_name", "")).casefold():
            st.success("Correct!")
        else:
            st.error("Not quite — try again.")
    reveal_button(item, ["qap", "accessory_minerals", "rock_name"])
    if st.button("Next specimen", key=f"hand_next_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}"):
        next_question()

def render_aphanitic(item, minerals):
    show_image(item.get("image"), "Thin section")
    a = item.get("answers", {})
    idx = st.session_state.quiz_index
    run = st.session_state.quiz_run_id
    st.markdown("#### Step 1 — Phenocryst mineralogy")
    phen_choices = item.get("phenocryst_options", minerals)
    phen = st.multiselect("Which minerals occur as phenocrysts?", phen_choices, key=f"aph_phen_{run}_{idx}")
    if st.button("Check phenocrysts", key=f"aph_phen_check_{run}_{idx}"):
        target = set(a.get("phenocrysts", []))
        if set(phen) == target:
            st.success("Correct!")
        else:
            st.error("Not quite. Try again.")
    st.markdown("#### Step 2 — Phenocryst abundance and composition")
    total = st.number_input("Total phenocrysts (% of whole rock)", 0, 100, 0, 1, key=f"aph_total_{run}_{idx}")
    phen_values = {}
    for m in a.get("phenocryst_percentages", {}).keys():
        phen_values[m] = st.number_input(f"{m} (% of whole rock)", 0, 100, 0, 1, key=f"aph_p_{run}_{idx}_{m}")
    if st.button("Check phenocryst percentages", key=f"aph_p_check_{run}_{idx}"):
        feedback_numeric("Total phenocrysts", total, a.get("phenocryst_total"))
        for m, val in phen_values.items():
            feedback_numeric(m, val, a.get("phenocryst_percentages", {}).get(m))
    st.markdown("#### Step 3 — Matrix mineralogy")
    matrix_options = item.get("matrix_options", minerals)
    matrix = st.multiselect("Which minerals occur in the matrix?", matrix_options, key=f"aph_matrix_{run}_{idx}")
    if st.button("Check matrix minerals", key=f"aph_matrix_check_{run}_{idx}"):
        if set(matrix) == set(a.get("matrix_minerals", [])):
            st.success("Correct!")
        else:
            st.error("Not quite. Try again.")
    st.markdown("#### Step 4 — Matrix composition")
    matrix_total = st.number_input("Total matrix (% of whole rock)", 0, 100, 0, 1, key=f"aph_mtotal_{run}_{idx}")
    matrix_values = {}
    for m in a.get("matrix_percentages", {}).keys():
        matrix_values[m] = st.number_input(f"{m} in matrix (% of whole rock)", 0, 100, 0, 1, key=f"aph_mp_{run}_{idx}_{m}")
    if st.button("Check matrix percentages", key=f"aph_mp_check_{run}_{idx}"):
        feedback_numeric("Total matrix", matrix_total, a.get("matrix_total"))
        for m, val in matrix_values.items():
            feedback_numeric(m, val, a.get("matrix_percentages", {}).get(m))
    st.markdown("#### Step 5 — Porosity")
    porosity = st.number_input("Estimate porosity (%)", 0, 100, 0, 1, key=f"aph_porosity_{run}_{idx}")
    if st.button("Check porosity", key=f"aph_porosity_check_{run}_{idx}"):
        feedback_numeric("Porosity", porosity, a.get("porosity"))
    reveal_button(item, ["phenocrysts", "phenocryst_total", "phenocryst_percentages", "matrix_minerals", "matrix_total", "matrix_percentages", "porosity", "rock_name"])
    if st.button("Next specimen", key=f"aph_next_{run}_{idx}"):
        next_question()

def render_phaneritic(item, minerals):
    show_image(item.get("image"), "Thin section")
    a = item.get("answers", {})
    idx, run = st.session_state.quiz_index, st.session_state.quiz_run_id
    st.markdown("#### Step 1 — Estimate QAP percentages")
    qap = {}
    cols = st.columns(3)
    for col, m in zip(cols, ["quartz", "k_feldspar", "plagioclase"]):
        with col:
            qap[m] = st.number_input(m.replace("_", " ").title() + " (%)", 0, 100, 0, 1, key=f"phan_qap_{run}_{idx}_{m}")
    if st.button("Check QAP estimates", key=f"phan_qap_check_{run}_{idx}"):
        for m, val in qap.items():
            feedback_numeric(m.replace("_", " ").title(), val, a.get("qap", {}).get(m))
    st.markdown("#### Step 2 — Normalize QAP to 100%")
    st.caption("Enter a normalized QAP estimate that sums to 100%, preserving your estimated ratio.")
    norm = {}
    cols = st.columns(3)
    for col, m in zip(cols, ["quartz", "k_feldspar", "plagioclase"]):
        with col:
            norm[m] = col.number_input(m.replace("_", " ").title() + " normalized (%)", 0, 100, 0, 1, key=f"phan_norm_{run}_{idx}_{m}")
    if st.button("Check normalized QAP", key=f"phan_norm_check_{run}_{idx}"):
        if sum(norm.values()) != 100:
            st.error(f"These values sum to {sum(norm.values())}%, not 100%.")
        else:
            target = a.get("qap_normalized", a.get("qap", {}))
            for m, val in norm.items():
                feedback_numeric(m.replace("_", " ").title(), val, target.get(m))
    st.markdown("#### Step 3 — Choose the rock type")
    type_options = item.get("rock_type_options", ["Granite", "Diorite", "Gabbro", "Granodiorite", "Syenite", "Tonalite"])
    rock_type = st.radio("Rock type", type_options, key=f"phan_type_{run}_{idx}")
    if st.button("Check rock type", key=f"phan_type_check_{run}_{idx}"):
        if rock_type.casefold() == str(item.get("rock_type", "")).casefold():
            st.success("Correct!")
        else:
            st.error("Not quite. Try again.")
    st.markdown("#### Step 4 — Estimate accessory minerals")
    accessory_values = {}
    for m in a.get("accessory_percentages", {}).keys():
        accessory_values[m] = st.number_input(f"{m} (% of whole rock)", 0, 100, 0, 1, key=f"phan_acc_{run}_{idx}_{m}")
    if st.button("Check accessory percentages", key=f"phan_acc_check_{run}_{idx}"):
        for m, val in accessory_values.items():
            feedback_numeric(m, val, a.get("accessory_percentages", {}).get(m))
    st.markdown("#### Step 5 — Name the rock")
    rock_choices = item.get("rock_name_options", [item.get("rock_name", "Unknown")])
    rock_name = st.selectbox("Rock name including accessory minerals", rock_choices, key=f"phan_name_{run}_{idx}")
    if st.button("Check rock name", key=f"phan_name_check_{run}_{idx}"):
        if rock_name.casefold() == str(item.get("rock_name", "")).casefold():
            st.success("Correct!")
        else:
            st.error("Not quite. Try again.")
    reveal_button(item, ["qap", "qap_normalized", "rock_type", "accessory_percentages", "rock_name"])
    if st.button("Next specimen", key=f"phan_next_{run}_{idx}"):
        next_question()

st.title("🪨 Igneous Rock Study Lab")
st.write("Practice mineral and igneous-rock identification with image-based questions. Attempts are unlimited; use **Reveal answer** whenever you need it.")

try:
    specimens = load_specimens()
except (OSError, json.JSONDecodeError) as exc:
    st.error(f"Could not read specimens.json: {exc}")
    st.stop()

st.session_state.all_specimens = specimens
minerals = mineral_options(specimens)
quiz_labels = {
    "mineral": "Mineral in thin section",
    "hand_sample": "Hand sample",
    "thin_section_rock": "Rock in thin section",
}
available = {k: sum(1 for s in specimens if s.get("type") == k) for k in quiz_labels}

with st.sidebar:
    st.header("Choose a quiz")
    quiz_label = st.radio("Quiz type", list(quiz_labels.values()))
    selected_type = next(k for k, v in quiz_labels.items() if v == quiz_label)
    st.caption(f"{available[selected_type]} specimen(s) currently available")
    question_count = st.number_input("Questions per round", min_value=1, max_value=50, value=5)
    if st.button("Start / restart quiz", type="primary", use_container_width=True):
        st.session_state.quiz_finished = False
        start_quiz(specimens, selected_type, int(question_count))
    st.divider()
    st.markdown("**Adding your own specimens**")
    st.write("Edit `specimens.json` and put image files in the `images/` folders. See `README.md` for the data format.")

if st.session_state.get("quiz_started", False):
    if st.session_state.quiz_type != selected_type:
        st.info("Choose **Start / restart quiz** to switch quiz types.")
    else:
        idx = st.session_state.quiz_index
        item = st.session_state.quiz_items[idx]
        question_header(item, idx, len(st.session_state.quiz_items))
        if item.get("type") == "mineral":
            render_mineral(item, minerals)
        elif item.get("type") == "hand_sample":
            render_hand_sample(item, minerals)
        elif item.get("type") == "thin_section_rock":
            if item.get("texture", "phaneritic").lower() == "aphanitic":
                render_aphanitic(item, minerals)
            else:
                render_phaneritic(item, minerals)
elif st.session_state.get("quiz_finished", False):
    st.success("Round complete! Great work.")
    if st.button("Start another round"):
        st.session_state.quiz_finished = False
        start_quiz(specimens, selected_type, int(question_count))
else:
    st.info("Choose a quiz type in the sidebar and press **Start / restart quiz**.")
    st.markdown("### Current specimen counts")
    st.write({quiz_labels[k]: v for k, v in available.items()})
