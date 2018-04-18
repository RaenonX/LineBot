import re
import requests

import itertools

def extract_link(str):
    exactMatch = re.compile(r"HTTPS?://[^\s\\、]+", re.UNICODE)
    print(exactMatch.findall(str))
    return exactMatch.findall(str)

##### GIF Test

def is_gif_link(str):
    return str.endswith('.gif')

##### IMGUR

def is_imgur_link(str):
    return str.lower().startswith("https://i.imgur.com")

def make_cases(str):
    return map(''.join, itertools.product(*zip(str.upper(), str.lower())))

def extract_imgur_id(str):
    return str.replace("HTTPS://I.IMGUR.COM/", "").replace(".JPG", "").replace(".PNG", "")

def test_imgur_image(image_url):
    cs = set(make_cases(extract_imgur_id(image_url)))
    match = set()
    len_cs = len(cs)

    for n, test in enumerate(cs, start=1):
        print("{}/{} ({} match)".format(n, len_cs, len(match)))
        try:
            req = requests.get("https://i.imgur.com/{}.jpg".format(test))
            if req.url != "https://i.imgur.com/removed.png":
                match.add(test)
        except:
            match.add("ERROR - https://i.imgur.com/{}.jpg".format(test))

    return match

#### FACEBOOK

def is_facebook_link(str):
    return str.upper().startswith("HTTPS://WWW.FACEBOOK.COM/")

#### BAHAMUT

def is_bahamut_link(str):
    return str.upper().startswith("HTTPS://FORUM.GAMER.COM.TW/C.PHP") or str.upper().startswith("HTTPS://M.GAMER.COM.TW/FORUM/C.PHP") \
        or str.upper().startswith("HTTPS://FORUM.GAMER.COM.TW/B.PHP") or str.upper().startswith("HTTPS://M.GAMER.COM.TW/FORUM/B.PHP")

def replace_incorrect(str):
    return str.lower().replace("c.php", "C.php").replace("sna", "snA").replace("b.php", "B.php").replace("a.php", "A.php").replace("snb", "snB")

#### OTHER

def is_other_lowerable_link(str):
    ALLOW = ["HTTPS://API-DEFRAG-AP.WRIGHTFLYER.NET/", "HTTPS://RATSOUNDS.GITHUB.IO/", "HTTPS://SDL-STICKERSHOP.LINE.NAVER.JP/STICKERSHOP"]
    return any(str.upper().startswith(prefix) for prefix in ALLOW)

#### GOO.GL

def is_googl_short(str):
    return str.lower().startswith("https://goo.gl")

def extract_googl_id(str):
    return str.replace("HTTPS://GOO.GL/", "")

def test_googl_short(image_url):
    cs = set(make_cases(extract_googl_id(image_url)))
    match = set()
    len_cs = len(cs)

    for n, test in enumerate(cs, start=1):
        print("{}/{} ({} match)".format(n, len_cs, len(match)))
        try:
            req = requests.get("https://goo.gl/{}".format(test))
            if req.status_code != 404:
                match.add("https://goo.gl/{}".format(test))
        except:
            match.add("ERROR - https://goo.gl/{}".format(test))

    return match

with open("data_fixed_v1_part99.csv", mode="w", encoding="utf-8") as out_:
    count = 0
	
    for line in ["HTTPS://I.IMGUR.COM/OSVMRLJ.JPG"]:
        print(count)

        for link in extract_link(line):
            if is_gif_link(link):
                line = line.replace(link, u"https://i.imgur.com/removed.png")
            elif is_imgur_link(link):
                match = test_imgur_image(link)

                if len(match) == 1:
                    line = line.replace(link, "https://i.imgur.com/{}.jpg".format(match.pop()))
                else:
                    line = line[:-1] + "," + ",".join(match)
            elif is_facebook_link(link) or is_other_lowerable_link(link):
                line = line.replace(link, link.lower())
            elif is_bahamut_link(link):
                line = line.replace(link, replace_incorrect(link))
            elif is_googl_short(link):
                match = test_googl_short(link)

                if len(match) == 1:
                    line = line.replace(link, "https://goo.gl/{}".format(match.pop()))
                else:
                    line = line[:-1] + "," + ",".join(match)
            else:
                line = line[:-1] + "," + link
            
        if line[-1] != "\n":
            line += "\n"

        out_.write(line)

        count += 1