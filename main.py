import argostranslate.package
import argostranslate.translate
import json
import os
from profanity_check import predict_prob
from enum import Enum
import sys
import re
import argparse
import polib

TARGET_LANG = "en"
source_dir = ""
file_mask = ""
error_threshold = 0.8
warning_threshold = 0.6
notice_threshold = 0.4
ok_threshold = 0.0


class TranslationFile:
    """Wrapper of a single translation file.
    """
    def __init__(self, lang: str, file_path: str, translations: dict[str, str], text: str):

        self.lang = lang
        self.file_path = file_path
        self.translations = translations
        self.text = text

        self.file_name = os.path.basename(file_path)


class WarningEnum(Enum):
    """Level corresponding to a GitHub annotation level.

    More info: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions
    """
    OK = 0
    NOTICE = 1
    WARNING = 2
    ERROR = 3


class StatusData:
    """Wrapper around annotation data.
    """
    def __init__(self, threshold: float, emoji: str, note: str, annotate: bool):

        self.threshold = threshold
        self.emoji = emoji
        self.note = note
        self.annotate = annotate


ANNOTATION_LEVELS = {
    WarningEnum.ERROR: StatusData(error_threshold, "🔴", "Highly likely offensive language", True),
    WarningEnum.WARNING: StatusData(warning_threshold, "🟠", "Likely offensive language", True),
    WarningEnum.NOTICE: StatusData(notice_threshold, "🟡", "Potentially offensive language", True),
    WarningEnum.OK: StatusData(ok_threshold, "🟢", "Ok", False),
}


def find_line(file_lines: list[str], lookup: str) -> int:
    """Find the line number in which `lookup` occurs. Returns -1 if no such string is found.
    """
    for num, line in enumerate(file_lines, 1):
        if lookup in line:
            return num

    return -1


def init_language(from_code: str, to_code: str) -> bool:
    """Initialize translations for the given language code mapping.

    `from_code` and `to_code` are the corresponding language codes, ex. "en".
    """
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    valid_packages = list(filter(lambda x: x.from_code == from_code and x.to_code == to_code, available_packages))

    if len(valid_packages) == 0:
        return False

    package_to_install = valid_packages[0]
    argostranslate.package.install_from_path(package_to_install.download())
    return True


def translate(text: str, from_code: str, to_code: str) -> str:
    """Translate source `text` into the given language, returning the translated string.

    `from_code` and `to_code` are the corresponding language codes, ex. "en".
    """
    return argostranslate.translate.translate(text, from_code, to_code)


def analyze(text: str) -> int:
    """Analyze `text` for profanity or sensitive content. Returns a value
    between 0 (not profanity) to 1 (profanity).
    """
    return predict_prob([text])[0]


def process_file(translation_file: TranslationFile):
    """Process a file containing translations, outputting GitHub annotations.
    """
    from_code = translation_file.lang
    to_code = TARGET_LANG

    if from_code == to_code:
        return

    log = []
    warning_level = WarningEnum.OK

    if not translation_file.text:
        log.append(f"::group::⚫️ Translating {translation_file.file_name}")
        log.append("No translations in file")
        log.append("::endgroup::")
        print("\n".join(log))
        return

    valid_language = init_language(from_code, to_code)
    if not valid_language:
        log.append(f"::group::⚪ Translating {translation_file.file_name}")
        log.append("Could not translate this language")
        log.append("::endgroup::")
        print("\n".join(log))
        return

    line_log: list[tuple[int, str]] = []

    for key, value in translation_file.translations.items():
        # json translations are not always str: str, but sometimes str: dict
        if not isinstance(value, str): continue

        line = find_line(translation_file.text.splitlines(), key)

        translated_text = translate(value, from_code, to_code)
        line_log.append((line, f"{line} ({from_code}): {value}"))
        line_log.append((line, "{} ({}): {}".format(" " * len(f"{line}"), to_code, translated_text)))

        # Show error for empty strings
        if value.strip() == "":
            if warning_level.value < WarningEnum.ERROR.value:
                warning_level = WarningEnum.ERROR
            line_log.append((line, f"::{WarningEnum.ERROR.name.lower()} file={translation_file.file_path},line={line}::EMPTY STRING"))
            continue

        # We consider both the original language string and the translated
        # string in case any bad english words in the original get lost in
        # translation. Usually the original language probability is very low due
        # to this working on english only.
        max_prob: int = max(analyze(translated_text), analyze(value))

        for level, status_data in ANNOTATION_LEVELS.items():
            if max_prob < status_data.threshold:
                continue
            if status_data.annotate:
                line_log.append((line, f"::{level.name.lower()} file={translation_file.file_path},line={line}::{status_data.note} ({max_prob:.2f}): \"{translated_text}\""))
            if warning_level.value < level.value:
                warning_level = level
            break

    # aggregate logs
    line_log.sort(key=lambda x: x[0])
    log.extend([x[1] for x in line_log])
    log.append("::endgroup::")
    log.insert(0, f"::group::{ANNOTATION_LEVELS[warning_level].emoji} Translating {translation_file.file_name}")
    print("\n".join(log))


def read_json(file_path: str) -> TranslationFile | None:
    """Attempt to read `file_path` as a JSON file, returning its contents as a `TranslationFile`
    """
    matches = re.match(file_mask, os.path.basename(file_path))
    if not matches or not matches.groups(1):
        return None

    try:
        with open(file_path, "r") as file:
            text = file.read()
            json_dict = json.loads(text)
            return TranslationFile(
                lang=matches.groups(1)[0],
                file_path=file_path,
                translations=json_dict,
                text=text
            )
    except:
        return None


def read_po(file_path: str) -> TranslationFile | None:
    """Attempt to read `file_path` as a PO file, returning its contents as a `TranslationFile`
    """
    matches = re.match(file_mask, os.path.basename(file_path))
    if not matches or not matches.groups(1):
        return None

    try:
        with open(file_path, "r") as file:
            text = file.read()
            po_file = polib.pofile(text)
            return TranslationFile(
                lang=matches.groups(1)[0],
                file_path=file_path,
                translations={entry.msgid: entry.msgstr for entry in po_file},
                text=text
            )
    except:
        return None


def read_file(file_path: str) -> TranslationFile | None:
    """Read in the given file as a `TranslationFile`.
    """
    json_file = read_json(file_path)
    if json_file is not None:
        return json_file

    po_file = read_po(file_path)
    if po_file is not None:
        return po_file

    return None


parser = argparse.ArgumentParser()
parser.add_argument(
    "--source", "-s",
    help="Path to directory with translation files.",
    type=str,
)
parser.add_argument(
    "--mask", "-m",
    help="RegEx pattern to match translation files.",
    type=str,
    required=True,
)
parser.add_argument(
    "--files", "-f",
    help="Comma-separated string of file paths to check. These should be compatible with the file mask.",
    type=str,
)
parser.add_argument(
    "--notice-level", "-n",
    help="Float threshold between 0 and 1 for notice-level alerts",
    type=str,
)
parser.add_argument(
    "--warning-level", "-w",
    help="Float threshold between 0 and 1 for warning-level alerts",
    type=str,
)
parser.add_argument(
    "--error-level", "-e",
    help="Float threshold between 0 and 1 for error-level alerts",
    type=str,
)
args = parser.parse_args()

if not args.files and not args.source:
    print("Either --source or --files is required")
    sys.exit()

file_mask = str(args.mask)

if args.notice_level:
    notice_threshold = float(args.notice_level)
if args.warning_level:
    warning_threshold = float(args.warning_level)
if args.error_level:
    error_threshold = float(args.error_level)

# --files
if args.files:
    for path in str(args.files).split(","):
        translation_file = read_file(path)
        if translation_file is not None:
            process_file(translation_file)

# --source
if args.source:
    source_dir = os.path.join(os.getcwd(), args.source)
    files = os.listdir(source_dir)
    files.sort()

    for filename in files:
        translation_file = read_file(os.path.join(source_dir, filename))
        if translation_file is not None:
            process_file(translation_file)
