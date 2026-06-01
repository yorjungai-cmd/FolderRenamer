import urllib.request, zipfile, os, io

URL = "https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip"
print("Downloading Inter font...")
data = urllib.request.urlopen(URL).read()
os.makedirs("resources/fonts", exist_ok=True)
with zipfile.ZipFile(io.BytesIO(data)) as z:
    for name in z.namelist():
        base = os.path.basename(name)
        if base.endswith(".ttf") and base.startswith("Inter-") and base:
            out = os.path.join("resources/fonts", base)
            with z.open(name) as src, open(out, "wb") as dst:
                dst.write(src.read())
            print(f"  {base}")
print("Done.")
