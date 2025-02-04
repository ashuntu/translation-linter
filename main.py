import argostranslate.package
import argostranslate.translate
import json
import os
from profanity_check import predict_prob


def find_line(file, lookup: str) -> int:

    for num, line in enumerate(file, 1):
        if lookup in line:
            return num
        
    return -1


def translate(file: list[str], from_code: str, to_code: str):

    if from_code == "en":
        return
    
    data = json.loads("\n".join(file))

    print(f"::group::Translating {from_code}")

    if not data:
        print("No data")
        return

    print("Installing packages")

    # Download and install Argos Translate package
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()

    valid_packages = list(filter(lambda x: x.from_code == from_code and x.to_code == to_code, available_packages))

    if len(valid_packages) == 0:
        print("COULD NOT TRANSLATE")
        return

    package_to_install = valid_packages[0]
    argostranslate.package.install_from_path(package_to_install.download())

    print("Translating")

    for key in data:
        if not data[key] or not isinstance(data[key], str): continue
        print(data[key])
        translated_text = argostranslate.translate.translate(data[key], from_code, to_code)
        print(translated_text)

        prob = predict_prob([translated_text])

        if prob >= 0.5:
            line = find_line(file, data[key])
            print(f"::warning file=translations/app_es.arb,line={line}::Potentially offense language")

        print()

    print("::endgroup::")


def main():

    source_dir = os.path.join(os.getcwd(), "translations")
    for filename in os.listdir(source_dir):
        with open(os.path.join(source_dir, filename)) as file:
            from_code = filename.removeprefix("app_").removesuffix(".arb")
            to_code = "en"
            translate(file.readlines(), from_code, to_code)
            print()


if __name__ == "__main__":
    main()
