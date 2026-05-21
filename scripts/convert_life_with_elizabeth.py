"""One-off converter for Life with Elizabeth messy workbook tab."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

SRC = Path(r"c:\Users\h3art\Downloads\Life with Elizabeth.xlsx")
OUT = Path(r"c:\Users\h3art\Downloads\Life_with_Elizabeth_import_ready.xlsx")

DEFAULT_STARS = "Betty White, Del Moore"

# Normalized title -> metadata (Season/Episode codes from Nikki workbook + researched air dates).
_RAW_EPISODES: dict[str, dict[str, str]] = {
    "bad mood - first kiss - ex-flame": {
        "se": "01_00",
        "date": "1953",
        "synopsis": (
            "Three separate stories in the life of our two protagonists. In the first story, "
            "Alvin comes home from work and finds Elizabeth in a foul humor; in the second "
            "segment, Elizabeth and Alvin recall their hesitant first kiss; and in the third "
            "tale, Alvin becomes jealous when Elizabeth invites an old beau to dinner."
        ),
    },
    "not for the birds - sleep problem - bowling night": {
        "se": "01_01",
        "date": "1953-10-07",
        "synopsis": (
            "Elizabeth brings home a parrot. Elizabeth gets angry with Alvin for falling asleep "
            "while she's chatting. One of Alvin's bowling buddies comes by and interrupts their dinner."
        ),
    },
    "scared silly - neighborhood slingshot - elmer garage": {
        "se": "01_02",
        "date": "1953-10-14",
        "synopsis": (
            "Elizabeth and Alvin read mystery books at night and every noise in the house scares "
            "them silly. Alvin whittles a slingshot on the front porch while Elizabeth makes him "
            "jealous flirting with the neighbor. They take their car to Elmer's Garage to have the "
            "horn fixed, but Alvin falls under the mechanic's hypnotic spell."
        ),
    },
    "photographer - honeymoon over - numb, deaf, blind": {
        "se": "01_04",
        "date": "1953-10-28",
        "synopsis": (
            "Elizabeth does not take seriously Alvin's attempt to win a photo contest. "
            "Elizabeth's performance of domestic duties falls short. The effects of physical "
            "events for Alvin, Elizabeth and Mrs. Skinridge alter their ability to act normally."
        ),
    },
    "carpentry - hypnotism - home movies": {
        "se": "01_05",
        "date": "1953-10-28",
        "synopsis": (
            "Elizabeth gets ideas from an improvement magazine and fixes Alvin's chair. "
            "Elizabeth gives hypnosis a try and thinks she's turned Alvin into a lighthouse. "
            "Mr. Fuddy tries to show his films to Alvin and Elizabeth but everything goes wrong."
        ),
    },
    "detective story - writing a speech - moosie on patio": {
        "se": "01_09",
        "date": "1953-11-13",
        "synopsis": (
            "Elizabeth and company get involved in some detective work. Elizabeth helps write a "
            "speech. Antics arise with Moosie on the patio."
        ),
    },
    "learn to drive day - the day moved in - alvin asks the boss home": {
        "se": "01_10",
        "date": "1953-12-02",
        "synopsis": (
            "Elizabeth wants Alvin to buy a new car. Alvin struggles replacing a fuse in the "
            "cellar. Alvin asks his boss Mr. Fuddy home for dinner."
        ),
    },
    "psychic - car repair - bird bath": {
        "se": "01_11",
        "date": "1953-11-05",
        "synopsis": (
            "Elizabeth schemes to go on Alvin's business trip; Alvin explains how the car engine "
            "works to Elizabeth; and Alvin's friend Richard is tasked with delivering a birdbath."
        ),
    },
    "scuttled schooner - tv aerial - dueling ping pong": {
        "se": "01_12",
        "date": "1953-11-27",
        "synopsis": (
            "Elizabeth and Alvin practise their sailing skills. The Whites get a new television "
            "set. Elizabeth and Alvin play ping pong."
        ),
    },
    "day off - varnishing floor - singing lesson": {
        "se": "01_13",
        "date": "1954-02-01",
        "synopsis": (
            "Elizabeth tries to break the news of her mother's visit to Alvin gently. Alvin "
            "manages to paint Elizabeth into a corner. Elizabeth decides to take singing lessons."
        ),
    },
    "mama's visit - bicycle picnic - nosey neighbors": {
        "se": "01_14",
        "date": "1954-03-08",
        "synopsis": (
            "In preparation for a visit from her mom Elizabeth turns the den into a bedroom with "
            "Alvin oblivious. Everything goes wrong when Alvin and Elizabeth bike into the country. "
            "Elizabeth recalls her early distaste for a busybody neighbor."
        ),
    },
    "moosie in kitchen - jungle living room - underhills for dinner": {
        "se": "01_17",
        "date": "1954-02-03",
        "synopsis": (
            "Elizabeth needs help from a man in fixing her husband's dinner. Elizabeth decorates "
            "the house in a jungle theme to distract from a problem. Alvin becomes flirtatious with "
            "friend Claudette Underhill while his wife is stuck with her dullard husband."
        ),
    },
    "black eye - momma breakfast - missing receptionist": {
        "se": "01_18",
        "date": "1954-02-22",
        "synopsis": (
            "Elizabeth gives herself a shiner the same evening Alvin's co-worker Mr. Underhill "
            "comes to dinner. Elizabeth and Alvin try to keep quiet when her mother visits and "
            "sleeps in. Elizabeth disastrously fills in at Alvin's office for a sick employee."
        ),
    },
    "bonus check - house cleaning - richard's mistake": {
        "se": "01_19",
        "date": "1954-03-01",
        "synopsis": (
            "Elizabeth and Alvin are planning a long weekend, but they can't leave until Alvin's "
            "bonus check arrives in the mail and the postman is late on his rounds; Elizabeth "
            "comes down with the urge to do some serious house cleaning; Elizabeth and Alvin try "
            "to patch up their neighbors' matrimonial squabble that started when the husband "
            "shaved off his mustache without consulting his wife first."
        ),
    },
    "oak tree - tv repair - drive-in": {
        "se": "01_20",
        "date": "1955-02-07",
        "synopsis": (
            "Elizabeth tries to convince Alvin to let her plant an oak tree in the middle of their "
            "patio; Alvin attempts to repair his malfunctioning television set by himself; Elizabeth "
            "and Alvin attempt to deal with a charmless carhop at a drive-in movie theater."
        ),
    },
    "morning grouch - shopping trip - tax day": {
        "se": "01_21",
        "date": "1955-07-14",
        "synopsis": (
            "The couple get into an argument that's more twist than shout. Elizabeth gets deeply "
            "involved in shopping. An open door for the tax man is used by a thief."
        ),
    },
    "check book - late party - piano tuner": {
        "se": "01_22",
        "date": "1955-08-04",
        "synopsis": (
            "Alvin has to do some office work at home, but Elizabeth won't stop talking. Elizabeth "
            "and Alvin prepare to dine out. It's fix-it day and the piano tuner calls."
        ),
    },
    "lobster avoidance - recycling overload - sea sickness": {
        "se": "01_23",
        "date": "1955-08-12",
        "synopsis": (
            "Elizabeth tries to stuff Alvin with salad and bread so he has no room for lobster. "
            "Elizabeth inundates the milkman with recycling. Elizabeth and Alvin are on a sea "
            "cruise, and Elizabeth keeps getting seasick."
        ),
    },
    "mama's letter - lodge dinner - richard gets fired": {
        "se": "01_24",
        "date": "1955-08-19",
        "synopsis": (
            "Mama's letter has such poor penmanship, they have to call her. Elizabeth complains "
            "about Alvin's lodge dinners, until she gets invited. Richard gets fired from his job."
        ),
    },
    "car stolen - fence painting - real estate": {
        "se": "01_25",
        "date": "1955-08-27",
        "synopsis": (
            "Elizabeth must tell Alvin their car was stolen. Elizabeth and Alvin paint the fence "
            "around their patio. Alvin and Richard buy a cabin without telling Elizabeth."
        ),
    },
    "relaxing afternoon - hanging drapes - bulldog": {
        "se": "01_26",
        "date": "1955-09-01",
        "synopsis": (
            "Over breakfast Elizabeth and Alvin decide to share each other's annoying habits. "
            "Later Elizabeth has trouble with curtains and Alvin makes things worse. Alvin's old "
            "buddy visits, treating Elizabeth with such courtesy Alvin ruins it by acting as usual."
        ),
    },
    "phone calls to work - girl scout trip - census taker": {
        "se": "01_27",
        "date": "1955-09-09",
        "synopsis": (
            "Elizabeth pesters Alvin with her constant inconsequential phone calls to his office. "
            "Elizabeth asks Alvin to quiz her on the Girl Scout leader's handbook. Elizabeth "
            "bedevils a poor census taker."
        ),
    },
    "collection agency - monster green eyes - good neighbor": {
        "se": "01_28",
        "date": "1954",
        "synopsis": (
            "A notice about an overdue bill concerns Elizabeth but she doesn't recall the purchase. "
            "Alvin expresses admiration for a beautiful actress and Elizabeth becomes jealous. "
            "Neighbors who are jingle writers run some by Alvin and Elizabeth."
        ),
    },
    "everything goes wrong - kind to animals - babysitting": {
        "se": "01_29",
        "date": "1954",
        "synopsis": (
            "Elizabeth sustains a lot of minor injuries. Elizabeth and Alvin observe some animals "
            "in the backyard. Babysitting leads to chaos."
        ),
    },
    "psychological study - mental telepathy - golf practice": {
        "se": "01_30",
        "date": "1954",
        "synopsis": (
            "Elizabeth's ego gets in the way. Elizabeth and Alvin experiment with mental telepathy. "
            "Alvin tries to practice golf at home."
        ),
    },
    "ping pong - leaking roof - vacuum salesman": {
        "se": "01_31",
        "date": "1954-02-24",
        "synopsis": (
            "Alvin's competitive nature gets the better of him after he wins his ping pong match "
            "against Elizabeth. A thunderstorm awakens Elizabeth and Alvin, who discover their roof "
            "is far from repaired. A vacuum cleaner salesman finds more than he bargained for."
        ),
    },
    "nursery rhymes - 1st business - lake allergies": {
        "se": "01_08",
        "date": "1953-11-25",
        "synopsis": (
            "Alvin is studying nursery rhymes to be prepared for the visit of Elizabeth's four year "
            "old niece. Elizabeth is in distress when Alvin for the first time in their marriage is "
            "going away on a short business trip. Alvin and Elizabeth stay over the weekend in "
            "Moosie's cabin and Elizabeth won't go to bed because of spiders."
        ),
    },
}


def clean(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def norm(text: str) -> str:
    s = clean(text).lower()
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\ufffd", "'")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


EPISODES = {norm(title): meta for title, meta in _RAW_EPISODES.items()}


def format_airdate(value) -> str:
    if not clean(value):
        return ""
    if isinstance(value, (int, float)) and not pd.isna(value):
        year = int(value)
        if 1900 <= year <= 2100:
            return str(year)
    text = clean(value)
    if re.fullmatch(r"\d{4}", text):
        return text
    try:
        return pd.to_datetime(value).date().isoformat()
    except Exception:
        return text


def season_ep_key(se: str) -> tuple[int, int]:
    text = clean(se)
    if "_" in text:
        left, right = text.split("_", 1)
        try:
            return int(left), int(right)
        except ValueError:
            pass
    return 999, 999


def normalize_stars(stars: str) -> str:
    stars = clean(stars).replace("Del, Moore", "Del Moore")
    return stars or DEFAULT_STARS


def fix_episode_title(title: str) -> str:
    return clean(title).replace("\ufffd", "'").replace("\u2019", "'")


def lookup_episode(title: str) -> dict[str, str] | None:
    key = norm(title)
    if key in EPISODES:
        return EPISODES[key]
    for episode_key, meta in EPISODES.items():
        if episode_key in key or key in episode_key:
            return meta
    return None


def main() -> None:
    raw = pd.read_excel(SRC, sheet_name="Life With Elizabeth", header=None)
    rows: list[dict[str, str]] = []

    for row_index in range(2, len(raw)):
        record = raw.iloc[row_index]
        episode = clean(record.iloc[0])
        if not episode:
            continue

        meta = lookup_episode(episode)
        if not meta:
            raise SystemExit(f"No metadata for episode: {episode!r}")

        sheet_synopsis = clean(record.iloc[4] if len(record) > 4 else "")
        sheet_stars = normalize_stars(record.iloc[3] if len(record) > 3 else "")

        rows.append(
            {
                "Episode": fix_episode_title(episode),
                "Season/Episode": meta["se"],
                "TRT": "",
                "Year/Original Airdate": meta["date"],
                "Genre": "comedy_variety",
                "Playable": "Yes",
                "Stars": sheet_stars,
                "Synopsis": sheet_synopsis or meta["synopsis"],
                "Notes": "",
            }
        )

    rows.sort(key=lambda row: season_ep_key(row["Season/Episode"]))
    df = pd.DataFrame(rows)

    with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Life With Elizabeth", index=False)

    print(f"Wrote {len(df)} episodes to {OUT}")
    print(df[["Season/Episode", "Episode", "Year/Original Airdate", "Playable"]].to_string(index=False))
    print("Missing synopsis:", int((df["Synopsis"] == "").sum()))


if __name__ == "__main__":
    main()
