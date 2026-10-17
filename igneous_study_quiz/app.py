import json
import random
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "specimens.json"
IMAGE_DIR = BASE_DIR / "images"

st.set_page_config(page_title="Igneous Rock Study Lab", page_icon="🪨", layout="wide")

DEFAULT_MINERALS = [
    "Quartz", "K-feldspar", "Plagioclase", "Biotite", "Hornblende",
    "Olivine", "Pyroxene", "Muscovite", "Amphibole", "Magnetite",
    "Apatite", "Garnet", "None Visible"
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


def show_thin_section(item):
    """Display a thin-section image with a PPL/XPL toggle."""

    # Default to PPL the first time the app is used.
    if "thin_section_view" not in st.session_state:
        st.session_state.thin_section_view = "ppl"

    current_view = st.session_state.thin_section_view
    images = item.get("images", {})

    # Support both the new PPL/XPL format and the old single-image format.
    if images:
        image = images.get(current_view)

        if image:
            show_image(image, f"Thin section — {current_view.upper()}")
        else:
            st.warning(
                f"No {current_view.upper()} image has been added "
                "for this specimen."
            )
    else:
        show_image(
            item.get("image"),
            "Thin section — single image (PPL/XPL not configured)"
        )

    # Button switches the view without advancing the question.
    button_label = (
        "Switch to XPL" if current_view == "ppl"
        else "Switch to PPL"
    )

    if st.button(button_label, key="toggle_thin_section_view"):
        st.session_state.thin_section_view = (
            "xpl" if current_view == "ppl" else "ppl"
        )
        st.rerun()
def show_mineral(item):
    """Display one mineral image with a PPL/XPL toggle."""

    if "mineral_view" not in st.session_state:
        st.session_state.mineral_view = "ppl"

    question_key = (
        f"{st.session_state.quiz_run_id}-"
        f"{st.session_state.quiz_index}"
    )

    if st.session_state.get("mineral_pair_key") != question_key:
        pairs = item.get("image_pairs", [])

        st.session_state.current_mineral_pair = (
            random.choice(pairs) if pairs else None
        )

        st.session_state.mineral_pair_key = question_key

    pair = st.session_state.get("current_mineral_pair")

    if pair:
        show_image(
            pair.get(st.session_state.mineral_view),
            f"Mineral — {st.session_state.mineral_view.upper()}"
        )
    else:
        show_image(item.get("image"), "Mineral")

    button_text = (
        "Switch to XPL"
        if st.session_state.mineral_view == "ppl"
        else "Switch to PPL"
    )

    if st.button(button_text, key="toggle_mineral_view"):
        st.session_state.mineral_view = (
            "xpl"
            if st.session_state.mineral_view == "ppl"
            else "ppl"
        )
        st.rerun()

def reset_quiz():
    for key in list(st.session_state.keys()):
        if key.startswith("quiz_") or key.startswith("answer_"):
            del st.session_state[key]


def start_quiz(specimens, quiz_type, count):
    candidates = [
        s for s in specimens
        if s.get("type") == quiz_type
    ]

    if not candidates:
        st.error(
            "There are no specimens for this quiz type yet. "
            "Add some to specimens.json."
        )
        return

    # Shuffle only once, when a new round begins.
    random.shuffle(candidates)
    selected = candidates[:min(count, len(candidates))]

    # Store the complete question order in session state.
    st.session_state.quiz_items = selected
    st.session_state.quiz_index = 0
    st.session_state.quiz_type = quiz_type
    st.session_state.quiz_started = True
    st.session_state.quiz_finished = False

    # A new ID distinguishes this round from previous rounds.
    st.session_state.quiz_run_id = (
        st.session_state.get("quiz_run_id", 0) + 1
    )

    # Reset per-question image selection for the new round.
    st.session_state.pop("mineral_pair_key", None)
    st.session_state.pop("current_mineral_pair", None)
    st.session_state.pop("active_pair_key", None)
    st.session_state.pop("active_pair", None)

    st.rerun()


def get_answer(item, key, default=None):
    return item.get("answers", {}).get(key, default)

def feedback_numeric(label, entered, target, tolerance=10, suffix="%"):
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
    st.session_state.scroll_to_top = True

    if st.session_state.quiz_index + 1 < len(
        st.session_state.quiz_items
    ):
        st.session_state.quiz_index += 1
    else:
        st.session_state.quiz_started = False
        st.session_state.quiz_finished = True

    st.rerun()


def previous_question():
    if st.session_state.quiz_index > 0:
        st.session_state.scroll_to_top = True
        st.session_state.quiz_index -= 1
        st.rerun()


def render_mineral(item, all_minerals):
    show_mineral(item)
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
    col_prev, col_next = st.columns(2)

    with col_prev:
        if st.button(
                "← Previous question",
                key=f"prev_min_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}",
                disabled=st.session_state.quiz_index == 0,
                use_container_width=True,
        ):
            previous_question()

    with col_next:
        if st.button(
                "Next specimen →",
                key=f"next_min_{st.session_state.quiz_run_id}_{st.session_state.quiz_index}",
                use_container_width=True,
        ):
            next_question()


def render_hand_sample(item, minerals):
    show_image(item.get("image"), "Hand sample")
    answers = item.get("answers", {})
    idx = st.session_state.quiz_index
    run = st.session_state.quiz_run_id

    # STEP 1: QAP composition
    st.markdown("#### Step 1 — Estimate QAP composition")
    st.caption(
        "Estimate Quartz, K-feldspar and Plagioclase. "
        "Your three estimates must sum to 100%. "
        "Each mineral is graded within ±10 percentage points."
    )

    qap = {}
    cols = st.columns(3)

    for col, mineral in zip(
        cols, ["quartz", "k_feldspar", "plagioclase"]
    ):
        with col:
            qap[mineral] = st.number_input(
                mineral.replace("_", " ").title() + " (%)",
                min_value=0,
                max_value=100,
                value=0,
                step=5,
                key=f"hand_{run}_{idx}_{mineral}"
            )

    if st.button("Check QAP", key=f"hand_qap_{run}_{idx}"):
        if sum(qap.values()) != 100:
            st.error(
                f"Your estimates sum to {sum(qap.values())}%. "
                "Adjust them so they sum to 100%."
            )
        else:
            target = answers.get("qap", {})
            if not target:
                st.warning("No QAP answer key has been supplied.")
            else:
                correct = True
                for mineral, value in qap.items():
                    expected = target.get(mineral)
                    if expected is None or abs(value - expected) > 10:
                        correct = False

                if correct:
                    st.success("QAP composition correct!")
                else:
                    st.warning(
                        "Not quite. Check the individual estimates "
                        "below and try again."
                    )
                for mineral, value in qap.items():
                    feedback_numeric(
                        mineral.replace("_", " ").title(),
                        value,
                        target.get(mineral),
                        tolerance=10
                    )

    if st.button(
        "Reveal QAP answer", key=f"hand_reveal_qap_{run}_{idx}"
    ):
        st.write("**QAP answer:**", answers.get("qap", "Not supplied"))

    st.divider()

    # STEP 2: Accessory minerals
    st.markdown("#### Step 2 — Identify accessory minerals")

    accessory_options = item.get(
        "accessory_options", minerals
    )
    selected = st.multiselect(
        "Select the accessory mineral(s) present",
        accessory_options,
        key=f"hand_access_{run}_{idx}"
    )

    if st.button(
        "Check accessory minerals",
        key=f"hand_check_access_{run}_{idx}"
    ):
        target = set(answers.get("accessory_minerals", []))

        if set(selected) == target:
            st.success("Correct!")
        else:
            st.error("Not quite. Try again.")

    if st.button(
        "Reveal accessory minerals",
        key=f"hand_reveal_access_{run}_{idx}"
    ):
        st.write(
            "**Answer:**",
            answers.get("accessory_minerals", "Not supplied")
        )

    st.divider()

    # STEP 3: Rock name
    st.markdown("#### Step 3 — Name the rock")

    rock_choices = item.get(
        "rock_options",
        sorted({
            s["rock_name"]
            for s in st.session_state.all_specimens
            if s.get("rock_name")
        })
    )

    rock = st.text_input(
        "Type the rock name",
        key=f"hand_rock_{run}_{idx}"
    )

    if st.button(
        "Check rock name", key=f"hand_check_rock_{run}_{idx}"
    ):
        if rock.casefold() == str(item.get("rock_name", "")).casefold():
            st.success("Correct!")
        else:
            st.error("Not quite. Try again.")

    if st.button(
        "Reveal rock name", key=f"hand_reveal_rock_{run}_{idx}"
    ):
        st.write("**Answer:**", item.get("rock_name", "Not supplied"))

    if st.button("Reveal all answers", key=f"hand_reveal_all_{run}_{idx}"):
        st.write("**QAP:**", answers.get("qap", "Not supplied"))
        st.write(
            "**Accessory minerals:**",
            answers.get("accessory_minerals", "Not supplied")
        )
        st.write("**Rock name:**", item.get("rock_name", "Not supplied"))
        if item.get("explanation"):
            st.info(item["explanation"])

    col_prev, col_next = st.columns(2)

    with col_prev:
        if st.button(
                "← Previous question",
                key=f"prev_hand_{run}_{idx}",
                disabled=idx == 0,
                use_container_width=True,
        ):
            previous_question()

    with col_next:
        if st.button(
                "Next specimen →",
                key=f"hand_next_{run}_{idx}",
                use_container_width=True,
        ):
            next_question()


def render_thin_section_rock(item, minerals):
    show_thin_section(item)

    answers = item.get("answers", {})
    idx = st.session_state.quiz_index
    run = st.session_state.quiz_run_id

    # STEP 1: QAP composition
    st.markdown("#### Step 1 — Estimate QAP composition")
    st.caption(
        "Estimate Quartz, K-feldspar and Plagioclase normalized to 100% "
        "Your three estimates must sum to 100%. "
        "Each mineral is graded within ±10 percentage points."
    )

    qap = {}
    cols = st.columns(3)

    for col, mineral in zip(
        cols, ["quartz", "k_feldspar", "plagioclase"]
    ):
        with col:
            qap[mineral] = st.number_input(
                mineral.replace("_", " ").title() + " (%)",
                min_value=0,
                max_value=100,
                value=0,
                step=5,
                key=f"thin_qap_{run}_{idx}_{mineral}"
            )

    if st.button("Check QAP", key=f"thin_qap_check_{run}_{idx}"):
        if sum(qap.values()) != 100:
            st.error(
                f"Your estimates sum to {sum(qap.values())}%. "
                "Adjust them so they sum to 100%."
            )
        else:
            target = answers.get(
                "qap_normalized", answers.get("qap", {})
            )

            if not target:
                st.warning("No QAP answer key has been supplied.")
            else:
                correct = all(
                    mineral in target
                    and abs(value - target[mineral]) <= 10
                    for mineral, value in qap.items()
                )

                if correct:
                    st.success("QAP composition correct!")
                else:
                    st.warning(
                        "Not quite. Check the individual estimates "
                        "below and try again."
                    )

                for mineral, value in qap.items():
                    feedback_numeric(
                        mineral.replace("_", " ").title(),
                        value,
                        target.get(mineral),
                        tolerance=10
                    )

    if st.button(
        "Reveal QAP answer", key=f"thin_qap_reveal_{run}_{idx}"
    ):
        st.write(
            "**QAP answer:**",
            answers.get(
                "qap_normalized", answers.get("qap", "Not supplied")
            )
        )

    st.divider()

    # STEP 2: Accessory mineral identification
    st.markdown("#### Step 2 — Identify accessory minerals")

    # Use an explicit answer list if supplied. Otherwise, use the
    # keys of accessory_percentages as the correct mineral list.
    accessory_targets = answers.get("accessory_minerals")
    if accessory_targets is None:
        accessory_targets = list(
            answers.get("accessory_percentages", {}).keys()
        )

    accessory_options = item.get(
        "accessory_options",
        item.get("mineral_options", minerals)
    )

    selected = st.multiselect(
        "Select the accessory mineral(s) present",
        accessory_options,
        key=f"thin_access_{run}_{idx}"
    )

    if st.button(
        "Check accessory minerals",
        key=f"thin_access_check_{run}_{idx}"
    ):
        if set(selected) == set(accessory_targets):
            st.success("Correct!")
        else:
            st.error("Not quite. Try again.")

    if st.button(
        "Reveal accessory minerals",
        key=f"thin_access_reveal_{run}_{idx}"
    ):
        st.write("**Answer:**", accessory_targets or "Not supplied")

    st.divider()

    # STEP 3: Full rock name
    st.markdown("#### Step 3 — Name the rock")

    rock_choices = item.get(
        "rock_name_options",
        item.get("rock_options", [])
    )

    if not rock_choices and item.get("rock_name"):
        rock_choices = [item["rock_name"]]

    rock = st.text_input(
        "Type the rock name",
        key=f"thin_rock_{run}_{idx}"
    )

    if st.button(
        "Check rock name", key=f"thin_rock_check_{run}_{idx}"
    ):
        if rock.casefold() == str(item.get("rock_name", "")).casefold():
            st.success("Correct!")
        else:
            st.error("Not quite. Try again.")

    if st.button(
        "Reveal rock name", key=f"thin_rock_reveal_{run}_{idx}"
    ):
        st.write("**Answer:**", item.get("rock_name", "Not supplied"))

    if st.button(
        "Reveal all answers", key=f"thin_reveal_all_{run}_{idx}"
    ):
        st.write(
            "**QAP:**",
            answers.get(
                "qap_normalized", answers.get("qap", "Not supplied")
            )
        )
        st.write("**Accessory minerals:**", accessory_targets or "Not supplied")
        st.write("**Rock name:**", item.get("rock_name", "Not supplied"))
        if item.get("explanation"):
            st.info(item["explanation"])

    col_prev, col_next = st.columns(2)

    with col_prev:
        if st.button(
                "← Previous question",
                key=f"prev_thin_{run}_{idx}",
                disabled=idx == 0,
                use_container_width=True,
        ):
            previous_question()

    with col_next:
        if st.button(
                "Next specimen →",
                key=f"thin_next_{run}_{idx}",
                use_container_width=True,
        ):
            next_question()


st.title("🪨 Igneous Rock Study Lab")

# Scroll the main Streamlit page to the top after navigation.
if st.session_state.pop("scroll_to_top", False):
    components.html(
        """
        <script>
        const scrollToTop = () => {
            try {
                const doc = window.parent.document;

                const candidates = [
                    doc.querySelector('[data-testid="stMain"]'),
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.querySelector('section.main')
                ];

                for (const el of candidates) {
                    if (el) {
                        el.scrollTo({
                            top: 0,
                            behavior: "auto"
                        });
                    }
                }

                window.parent.scrollTo(0, 0);
            } catch (e) {
                console.log("Could not scroll parent page:", e);
            }
        };

        scrollToTop();
        setTimeout(scrollToTop, 100);
        </script>
        """,
        height=1,
    )

st.write("Practice mineral and igneous-rock identification with image-based questions. Attempts are unlimited; use **Reveal answer** whenever you need it.")

try:
    specimens = load_specimens()
except (OSError, json.JSONDecodeError) as exc:
    st.error(f"Could not read specimens.json: {exc}")
    st.stop()

st.session_state.all_specimens = specimens
minerals = [item['id'] for item in specimens]
##minerals = DEFAULT_MINERALS
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
            render_hand_sample(item, DEFAULT_MINERALS)
        elif item.get("type") == "thin_section_rock":
            render_thin_section_rock(item, DEFAULT_MINERALS)
elif st.session_state.get("quiz_finished", False):
    st.success("Round complete! Great work.")
    if st.button("Start another round"):
        st.session_state.quiz_finished = False
        start_quiz(specimens, selected_type, int(question_count))
else:
    st.info("Choose a quiz type in the sidebar and press **Start / restart quiz**.")
    st.markdown("### Current specimen counts")
    st.write({quiz_labels[k]: v for k, v in available.items()})
