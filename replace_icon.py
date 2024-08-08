import sys
import shutil
import subprocess
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from pathlib import Path

KEYSTORE = Path("./bin/freekey.keystore")
ALIAS = "freekey"
PASSWORD = "123456"

GREEN = "\033[92m"
RED = "\033[91m"
ENDC = "\033[0m"


def infoprint(msg):
    print(f"{GREEN}[INFO] {msg}{ENDC}")


def errorprint(msg):
    print(f"{RED}[ERROR] {msg}{ENDC}")


def unpack_apk(APK, OUTPUT):
    UNPACKED = OUTPUT / "unpacked"
    infoprint(f'Unpacking "{APK}" to "{UNPACKED}"...')
    UNPACKED.mkdir(parents=True, exist_ok=True)
    with ZipFile(APK, "r") as zipf:
        zipf.extractall(UNPACKED)
    return UNPACKED


def repack_apk(UNPACKED, OUTPUT, APK):
    APK_PACKED = OUTPUT / f"{APK.stem}_repacked.apk"
    infoprint(f'Packing "{UNPACKED}" to "{APK_PACKED}"...')

    no_compress_exts = {".so", ".png", ".jpg", ".ogg", ".mp3"}
    no_compress_files = {"resources.arsc"}
    no_compress_dirs = {"assets/"}

    with ZipFile(APK_PACKED, "w") as zipf:
        for src_file in UNPACKED.rglob("*"):
            if src_file.is_file():
                if (
                    src_file.suffix in no_compress_exts
                    or src_file.name in no_compress_files
                ):
                    compress_type = ZIP_STORED
                    compress_level = None
                elif any(
                    src_file.parts[i] == nc.rstrip("/").split("/")[-1]
                    for i in range(len(src_file.parts))
                    for nc in no_compress_dirs
                ):
                    compress_type = ZIP_STORED
                    compress_level = None
                else:
                    compress_type = ZIP_DEFLATED
                    compress_level = 9

                zipf.write(
                    src_file,
                    src_file.relative_to(UNPACKED),
                    compress_type=compress_type,
                    compresslevel=compress_level,
                )
    return APK_PACKED


def replace_files(SOURCE, TARGET):
    infoprint(f'Replacing files from "{SOURCE}" to "{TARGET}"...')
    for src_file in SOURCE.rglob("*"):
        if src_file.is_file():
            dst_file = TARGET / src_file.relative_to(SOURCE)
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src_file, dst_file)


def align_and_sign(APK_PACKED, keystore, alias, password):
    BIN = Path("./bin")
    ZIPALIGN = BIN / "zipalign"
    APKSIGNER = BIN / "apksigner.bat"
    APK_ALIGNED = APK_PACKED.with_name(f"{APK_PACKED.stem}_aligned.apk")
    APK_SIGNED = APK_ALIGNED.with_name(f"{APK_ALIGNED.stem}_signed.apk")

    infoprint(f'Aligning and signing "{APK_PACKED}" to "{APK_SIGNED}"...')
    subprocess.run([ZIPALIGN, "-p", "-f", "4", APK_PACKED, APK_ALIGNED], check=True)
    infoprint(f'Signing "{APK_ALIGNED}" to "{APK_SIGNED}"...')
    subprocess.run(
        [
            APKSIGNER,
            "sign",
            "--ks",
            keystore,
            "--ks-key-alias",
            alias,
            "--ks-pass",
            f"pass:{password}",
            "--out",
            APK_SIGNED,
            APK_ALIGNED,
        ],
        check=True,
    )
    return APK_SIGNED


def main(APK):
    infoprint(f'Replacing icon in "{APK}"...')
    if not APK.suffix == ".apk":
        errorprint(f'The provided file "{APK}" is not an APK file.')
        sys.exit(1)

    OUTPUT = Path("./out")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()

    DIF = Path("./dif")
    UNPACKED = unpack_apk(APK, OUTPUT)
    replace_files(DIF, UNPACKED)
    APK_PACKED = repack_apk(UNPACKED, OUTPUT, APK)
    APK_SIGNED = align_and_sign(APK_PACKED, KEYSTORE, ALIAS, PASSWORD)
    shutil.copy(APK_SIGNED, APK.with_name(f"{APK.stem}_replaced.apk"))
    infoprint(f'Replaced APK saved as "{APK_SIGNED}"')


if __name__ == "__main__":
    if len(sys.argv) != 2:
        infoprint("Usage: replace_icon.py <apk_file>")
        sys.exit(1)
    main(Path(sys.argv[1]))
