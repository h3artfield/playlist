# Nikki workbook tab audit

**File:** `C:/Users/h3art/Downloads/2024 Nikki Spreadsheets.xlsx`  

**Tab count:** 48  

Each section is one Excel tab. **Try-load** uses `binge_schedule.nikki.load_sheet` with the inferred parser style; if the tab is wired in `config/april_2026.yaml`, the YAML `nikki_row_filter` (e.g. Carol green cells) is applied for the count.

### Tabs with **0** parsed rows (fix first — wrong/missing headers or layout)

| # | Tab | Likely issue |
|---|-----|----------------|
| 9 | `NEW SHOWS` | Catalog layout (`Artist/Series`, `Title (INTERNAL)`…) — not standard Episode + Season/Episode |
| 10 | `Stingray` | No header row with `Episode` + `Season/Episode` in first rows; title/duration layout |
| 12 | `CPO Sharkey` | `S1_EP01` pattern in Episode column but **no** `Season/Episode` column — needs Texan-style parser or `nikki_columns` |
| 18 | `Hawkeye (color)` | Missing `Season/Episode` column in header — only Episode + Year + Stars |
| 23 | `FARSCAPE` | Single-column “boxed set” text rows — not tabular Nikki layout |
| 24 | `CANDID CAMERA` | Only `Episode` + `Synopsis` — missing required `Season/Episode` for standard loader |

---

## 1. `21 Jump Street`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `jump_street`

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `jmp`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | JMP_101 - 21 Jump Street: Pt 1 | 01_01 | 1987-04-12 00:00:00 | Johnny Depp, Frederic Forrest, Holly Robinson Peete | As part of a new police initiative a young lookin… |  |
| r3 | JMP_102 - 21 Jump Street: Pt 2 | 01_01 | 1987-04-12 00:00:00 | Johnny Depp, Frederic Forrest, Holly Robinson Peete | As part of a new police initiative a young lookin… |  |
| r4 | JMP_103 - America, What A Town | 01_02 | 1987-04-19 00:00:00 | Johnny Depp, Frederic Forrest, Holly Robinson Peete | Hanson investigates a car theft ring while Hoffs … |  |
| r5 | JMP_104 - Don’t Pet The Teacher | 01_03 | 1987-04-26 00:00:00 | Johnny Depp, Frederic Forrest, Holly Robinson Peete | Hanson investigates a series of breaking and ente… |  |
| r6 | JMP_105 - My Future’s So Bright, I Gotta Wear Shades | 01_04 | 1987-05-03 00:00:00 | Johnny Depp, Frederic Forrest, Holly Robinson Peete | Hanson and Penhall investigate the possible rape … |  |
| r7 | JMP_106 - The Worst Night Of Your Life | 01_05 | 1987-05-10 00:00:00 | Johnny Depp, Frederic Forrest, Holly Robinson Peete | Hoffs goes undercover at an all girls' school to … |  |
| r8 | JMP_107 - Gotta Finish The Riff | 01_06 | 1987-05-17 00:00:00 | Johnny Depp, Holly Robinson Peete, Peter DeLuise | After a teacher's car is pipe-bombed Hanson and H… |  |
| r9 | JMP_108 - Bad Influence | 01_07 | 1987-05-24 00:00:00 | Johnny Depp, Holly Robinson Peete, Peter DeLuise | Hanson and Penhall investigate the disappearance … |  |
| r10 | JMP_109 - Blindsided | 01_08 | 1987-05-31 00:00:00 | Johnny Depp, Holly Robinson Peete, Peter DeLuise | Hanson and Penhall go undercover to investigate d… |  |
| r11 | JMP_110 - Next Generation | 01_09 | 1987-06-07 00:00:00 | Johnny Depp, Holly Robinson Peete, Peter DeLuise | Hanson investigates a beating that is suspected t… |  |


### Try-load episodes: **103** rows parsed (with filters above if any)


---

## 2. `movies`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `movies`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Movies |  |  |  |  |  |  |
| r1 | Title | TRT | B&W/Color | Year | Genre | Stars | Synopsis |
| r2 | ‘Neath The Arizona Skies | 0:52:31 | B&W | 1934 | Drama, Western | John Wayne, Sheila Terry, Shirley Jean Rickert | A cowboy escorts a little girl, whose mother made… |
| r3 | 12 Days Of Christmas Eve | 1:28:18 | Color | 2004 | Comedy, Drama, Fantasy | Steven Weber, Stefanie von Preteen, Mark Krysko | A successful CEO meets a Latin American rep Chris… |
| r4 | 12 Hours To Live | 1:34:48 | Color | 2006 | Crime, Drama, Thriller | Ione Skye, Kevin Durand, Brittney Wilson | An FBI Agent must race against time to save the l… |
| r5 | 1918 | 1:33:16 | Color | 1985 | Drama | Willam Converse-Roberts, Hallie Foote, Matthew Br… | In a small Texas Town at the height of World War … |
| r6 | 3 Bullets For Ringo | 1:27:14 | Color | 1966 | Drama, Western | Gordon Mitchell, Mickey Hargitay, Milla Sonnoner | Ringo Carson has a tough life. First, he has a fa… |
| r7 | 39 Steps, The | 1:26:21 | B&W | 1935 | Crime, Mystery, Thriller | Robert Donat, Madeleine Carroll, Lucie Mannheim | A man in London tries to help a counter-espionage… |
| r8 | 43: The Richard Petty Story | 1:18:00 | Color | 1972 | Biography, Comedy, Drama | Darren McGavin, Kathie Browne, Noah Beery, Jr. | The career of stock-car racer Richard Petty is ch… |
| r9 | Abar | 1:41:54 | Color | 1977 | Action, Drama, Sci-Fi | J. Walter Smith, Tobar Mayo, Roxie Young | Upon moving into a bigoted neighborhood, the scie… |
| r10 | Abilene Town | 1:29:21 | B&W | 1946 | Western | Randolph Scott, Ann Dvorak, Edgar Buchanan | A sheriff tries to stop homesteader conflicts in … |
| r11 | Across The Tracks | 1:40:19 | Color | 1990 | Drama, Sport | Ricky Schroder, Brad Pitt, Carrie Snodgrass | A straight A student has his future derailed by h… |


### Try-load episodes: **1115** rows parsed (with filters above if any)


---

## 3. `Ace Crawford - Ace Crawford…Pri`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Ace Crawford…Private Eye |  |  |  |  |  |  |
| r1 | Episode | Season/Episode | TRT | Original Airdate | Stars | Synopsis | Notes |
| r2 | 8201 - Murder At Restful Hills | 01_01 | 0:24:34 | 1983-03-15 00:00:00 | Tim Conway, Joe Regalbuto, Billy Barty | Ace investigates the claims of Luana's grandmothe… |  |
| r3 | 8202 - Bull Bates | 01_02 | 0:24:36 | 1983-03-22 00:00:00 | Tim Conway, Joe Regalbuto, Billy Barty | Ace infiltrates a monster's warehouse but his hug… |  |
| r4 | 8203 - Inch In A Pinch | 01_03 | 0:24:41 | 1983-03-29 00:00:00 | Tim Conway, Billy Barty, Kimberly Bronson | Ace sees red when he discovers that his buddy Inc… |  |
| r5 | 8204 - The Microchip Caper | 01_04 | 0:24:44 | 1983-04-05 00:00:00 | Tim Conway, Billy Barty, Christine Belford | Ace is hired to test plant security for a compute… |  |
| r6 | 8205 - The Gentleman Bandit | 01_05 | 0:24:31 | 1983-04-12 00:00:00 | Tim Conway, Joe Regalbuto, Billy Barty | Ace goes undercover to foil a criminal targeting … |  |


### Try-load episodes: **5** rows parsed (with filters above if any)


---

## 4. `Annie Oakley`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | 01 Annie And Brass Collar | 01_01 | 1954-01-09 00:00:00 | Gail Davis, Jimmy Hawkins, Brad Johnson | Annie is called on to help find three men involve… |  |
| r3 | 02 Annie Trusts A Convict | 01_02 | 1954-01-16 00:00:00 | Gail Davis, Jimmy Hawkins, Brad Johnson | An old school friend of Annie's breaks out of jai… |  |
| r4 | 03 Gunplay | 01_03 | 1954-01-23 00:00:00 | Gail Davis, Jimmy Hawkins, Brad Johnson | With an outlaw at large and the Sheriff searching… |  |
| r5 | 04 Dude Stagecoach | 01_04 | 1954-01-30 00:00:00 | Gail Davis, Jimmy Hawkins, Brad Johnson | While awaiting word from the mine to see if they … |  |
| r6 | 05 Ambush Canyon | 01_05 | 1954-02-06 00:00:00 | Gail Davis, Jimmy Hawkins, Brad Johnson | The owner of the mine is bushwhacked, but lives l… |  |
| r7 | 06 Annie Calls Her Shots | 01_06 | 1954-02-13 00:00:00 | Gail Davis, Jimmy Hawkins, Brad Johnson | Annie and Lofty jail Dobie but he proclaims his i… |  |
| r8 | 07 Gal For Grandma | 01_07 | 1954-02-20 00:00:00 | Gail Davis, Jimmy Hawkins, Brad Johnson | The grandson of rich old cantankerous woman arriv… |  |
| r9 | 08 Annie And Silver Ace | 01_08 | 1954-02-27 00:00:00 | Gail Davis, Jimmy Hawkins, Brad Johnson | Tagg experiments with hypnosis and has Moose beli… |  |
| r10 | 09 Annie Finds Strange Treasure | 01_09 | 1954-03-06 00:00:00 | Gail Davis, Jimmy Hawkins, Brad Johnson | When Annie tries to save an old prospector from a… |  |
| r11 | 10 Cinder Trail | 01_10 | 1954-03-13 00:00:00 | Gail Davis, Jimmy Hawkins, Brad Johnson | A cattleman tries to take over the railroad so th… |  |


### Try-load episodes: **81** rows parsed (with filters above if any)


---

## 5. `Beverly Hillbillies - The Bever`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | The Beverly Hillbillies |  |  |  |  |  |
| r1 | Episode | Season/Episode | Original Airdate | Stars | Synopsis | Notes |
| r2 | Clampetts Strike Oil | 01_01 | 1962-09-26 00:00:00 | Buddy Epsen, Irene Ryan, Donna Douglas, Max Baer Jr. | Jed Clampett is told by a representative of an oi… |  |
| r3 | Getting Settled | 01_02 | 1962-10-03 00:00:00 | Buddy Epsen, Irene Ryan, Donna Douglas, Max Baer Jr. | The Clampetts begin to settle in their new home i… |  |
| r4 | Meanwhile Back At The Cabin | 01_03 | 1962-10-10 00:00:00 | Buddy Epsen, Irene Ryan, Donna Douglas, Max Baer Jr. | While Granny boils pool water for washing (due to… |  |
| r5 | Clampetts Meets Mrs. Drysdale | 01_04 | 1962-10-17 00:00:00 | Buddy Epsen, Irene Ryan, Donna Douglas, Max Baer Jr. | Mr. Drysdale panics when Mrs. Drysdale comes back… |  |
| r6 | Jed Buys Stock | 01_05 | 1962-10-24 00:00:00 | Buddy Epsen, Irene Ryan, Donna Douglas, Max Baer Jr. | Grannie prepares her special mash to help cure Mr… |  |
| r7 | Trick Or Treat | 01_06 | 1962-10-31 00:00:00 | Buddy Epsen, Irene Ryan, Donna Douglas, Max Baer Jr. | Granny wants to go home because folks is so unfri… |  |
| r8 | Servants, The | 01_07 | 1962-11-07 00:00:00 | Buddy Epsen, Irene Ryan, Donna Douglas, Max Baer Jr. | Ellie May starts wearing dresses but takes it as … |  |
| r9 | Jethro Goes To School | 01_08 | 1962-11-14 00:00:00 | Buddy Epsen, Irene Ryan, Donna Douglas, Max Baer Jr. | Jed enrolls Jethro at an exclusive Beverly Hills … |  |
| r10 | Elly’s First Date | 01_09 | 1962-11-21 00:00:00 | Buddy Epsen, Irene Ryan, Donna Douglas, Max Baer Jr. | Mr. Drysdale convinces his self-absorbed stepson … |  |
| r11 | Pygmalion And Elly | 01_10 | 1962-11-28 00:00:00 | Buddy Epsen, Irene Ryan, Donna Douglas, Max Baer Jr. | Sonny Drysdale decides he needs to be Pygmalion t… |  |


### Try-load episodes: **55** rows parsed (with filters above if any)


---

## 6. `Bonanza - Bonanza`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Bonanza |  |  |  |  |  |
| r1 | Episode | Season/Episode | Original Airdate | Stars | Synopsis | Notes |
| r2 | Gunman, The | 01_19 | 1960-01-23 00:00:00 | Lorne Greene, Michael Landon, Dan Blocker, Pernel… | Hoss and Little Joe are mistaken for bloodthirsty… |  |
| r3 | Fear Merchants, The | 01_20 | 1960-01-30 00:00:00 | Lorne Greene, Michael Landon, Dan Blocker, Pernel… | The Cartwrights come to the aid of a Chinese-Amer… |  |
| r4 | Spanish Grant, The | 01_21 | 1960-02-06 00:00:00 | Lorne Greene, Michael Landon, Dan Blocker, Pernel… | The Cartwrights try to disprove the validity of a… |  |
| r5 | Blood On The Land | 01_22 | 1960-02-13 00:00:00 | Lorne Greene, Michael Landon, Dan Blocker, Pernel… | Jeb Drummond is a murderous sheep herder that has… |  |
| r6 | Desert Justice | 01_23 | 1960-02-20 00:00:00 | Lorne Greene, Michael Landon, Dan Blocker, Pernel… | As is often the case on Bonanza, things are not a… |  |
| r7 | Stranger, The | 01_24 | 1960-02-27 00:00:00 | Lorne Greene, Michael Landon, Dan Blocker, Pernel… | Inspector Leduque comes from New Orleans to Virgi… |  |
| r8 | Escape To Ponderosa | 01_25 | 1960-03-05 00:00:00 | Lorne Greene, Michael Landon, Dan Blocker, Pernel… | Three deserters escaped from an Army stockade to … |  |
| r9 | Avenger, The | 01_26 | 1960-03-19 00:00:00 | Lorne Greene, Michael Landon, Dan Blocker, Pernel… | Ben and Adam are locked in jail, about to hung fo… |  |
| r10 | Last Trophy, The | 01_27 | 1960-03-26 00:00:00 | Lorne Greene, Michael Landon, Dan Blocker, Pernel… | An English couple comes to Ponderosa on vacation,… |  |
| r11 | San Francisco Holiday | 01_28 | 1960-04-02 00:00:00 | Lorne Greene, Michael Landon, Dan Blocker, Pernel… | While in San Francisco, two of Ben's hired hands … |  |


### Try-load episodes: **31** rows parsed (with filters above if any)


---

## 7. `Californians`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Original Airdate | B&W / Color | Stars | Synopsis |
| r2 | 101 - The Vigilantes Begin | 01_01 | 1957-09-24 00:00:00 | B & W | Adam Kennedy, Sean McClory, Nan Leslie | Arriving in San Francisco in search of gold, Dion… |
| r3 | 102 - All That Glitters | 01_02 | 1957-10-01 00:00:00 | B & W | Adam Kennedy, Sean McClory, Russ Bender | A gold prospector is about to be hung for attempt… |
| r4 | 103 - The Noose | 01_03 | 1957-10-08 00:00:00 | B & W | Adam Kennedy, Sean McClory, Nan Leslie | Vigilantes disagree on whether to try or to lynch… |
| r5 | 104 - The Avenger | 01_04 | 1957-10-15 00:00:00 | B & W | Adam Kennedy, Sean McClory, Herbert Rudley | Dion seeks vengeance when a reporter is murdered. |
| r6 | 105 - The Search For Lucy Manning | 01_05 | 1957-10-22 00:00:00 | B & W | Adam Kennedy, Sean McClory, Nan Leslie | Rev. Spangler tries to help a young girl involved… |
| r7 | 106 - The Lost Queue | 01_06 | 1957-10-29 00:00:00 | B & W | Adam Kennedy, Sean McClory, Nan Leslie | Thugs try to stop a group of Chinese immigrants f… |
| r8 | 107 - The Regulators | 01_07 | 1957-11-05 00:00:00 | B & W | Adam Kennedy, Sean McClory, Marie Windsor | To silence witnesses against their boss, outlaws … |
| r9 | 108 - Man From Boston | 01_08 | 1957-11-12 00:00:00 | B & W | Adam Kennedy, Sean McClory, Nan Leslie | Jack is shot by a renegade and Dion tries despera… |
| r10 | 109 - The Barber’s Boy | 01_09 | 1957-11-19 00:00:00 | B & W | Adam Kennedy, Sean McClory, Nan Leslie | The Vigilantes are helped by a boy in their strug… |
| r11 | 110 - The Magic Box | 01_10 | 1957-11-26 00:00:00 | B & W | Adam Kennedy, Sean McClory, Peggy McCay | Politics is a deadly game the way Martin Donovan … |


### Try-load episodes: **69** rows parsed (with filters above if any)


---

## 8. `The Commish`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | S01E01 - In The Best Of Families |  | 1991-09-28 00:00:00 | Michael Chiklis, Theresa Saldana, Kaj-Erik Eriksen | Tony is threatened with criminal negligence after… |  |
| r3 | S01E02 - Do You See What I See | 01_02 | 1991-10-05 00:00:00 | Michael Chiklis, Theresa Saldana, Kaj-Erik Eriksen | The commissioner sets out to trap a serial rapist… |  |
| r4 | S01E03 - The Poisoned Tree | 01_03 | 1991-10-12 00:00:00 | Michael Chiklis, Theresa Saldana, Kaj-Erik Eriksen | Rachel refuses to believe Tony when he tells her … |  |
| r5 | S01E04 - Nothing To Fear But Fear… | 01_04 | 1991-10-26 00:00:00 | Michael Chiklis, Theresa Saldana, Kaj-Erik Eriksen | After receiving a pair of baffling death threats,… |  |
| r6 | S01E05 - A Matter Of Life Or Death: Part 1 | 01_05 | 1991-10-26 00:00:00 | Michael Chiklis, Theresa Saldana, Kaj-Erik Eriksen | Tony starts the review process to become New York… |  |
| r7 | S01E06 - A Matter Of Life Or Death: Part 2 | 01_06 | 1991-11-02 00:00:00 | Michael Chiklis, Theresa Saldana, Kaj-Erik Eriksen | Tony discovers who is responsible for the disappe… |  |
| r8 | S01E07 - Behind The Storm Door | 01_07 | 1991-11-09 00:00:00 | Michael Chiklis, Theresa Saldana, Kaj-Erik Eriksen | Tony is pursued by a woman he suspects is filing … |  |
| r9 | S01E08 - The Hatchet | 01_08 | 1991-11-16 00:00:00 | Michael Chiklis, Theresa Saldana, Kaj-Erik Eriksen | Tony butts heads with both a tough cop who is ove… |  |
| r10 | S01E09 - Two Confessions | 01_09 | 1991-11-30 00:00:00 | Michael Chiklis, Theresa Saldana, Kaj-Erik Eriksen | Tony is doubly stymied when identical twins both … |  |
| r11 | S01E10 - The Commissioner’s Ball | 01_10 | 1991-12-07 00:00:00 | Michael Chiklis, Theresa Saldana, Kaj-Erik Eriksen | A serial killer has been mutilating the bodies of… |  |


### Try-load episodes: **95** rows parsed (with filters above if any)


---

## 9. `NEW SHOWS`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Artist/Series | Title (INTERNAL) | Sort Title | Description | Short Description | Amazon Channels Genre | Roku Genre Tags |
| r1 | For Better Or For Worse | For Better Or For Worse | For Better Or For Worse | Hosted by Kathleen McClellan, FOR BETTER OR FOR W… |  |  |  |
| r2 | For Better Or For Worse | For Better Or For Worse: Season 1 | For Better Or For Worse: S01 E00 | Hosted by Kathleen McClellan, FOR BETTER OR FOR W… |  |  |  |
| r3 | For Better Or For Worse | For Better Or For Worse: S1 E1 - Shannon & Erik | For Better Or For Worse: S01 E01 - Shannon & Erik | WOULD YOU LET YOUR FAMILY AND A PERFECT STRANGER … | Would you let your family and a perfect stranger … |  |  |
| r4 | For Better Or For Worse | For Better Or For Worse: S1 E2 - Amanda & Ian | For Better Or For Worse: S01 E02 - Amanda & Ian | WOULD YOU LET YOUR FAMILY AND A PERFECT STRANGER … | Would you let your family and a perfect stranger … |  |  |
| r5 | For Better Or For Worse | For Better Or For Worse: S1 E3 - Katrina & Christ… | For Better Or For Worse: S01 E03 - Katrina & Chri… | WOULD YOU HAND OVER THE WEDDING YOU'VE DREAMED OF… | This team has only seven days and five thousand d… |  |  |
| r6 | For Better Or For Worse | For Better Or For Worse: S1 E4 - Sharon & David | For Better Or For Worse: S01 E04 - Sharon & David | WOULD YOU HAND OVER THE WEDDING YOU'VE DREAMED OF… | Now this team has only seven days and five thousa… |  |  |
| r7 | For Better Or For Worse | For Better Or For Worse: S1 E5 - Kelli & Randi | For Better Or For Worse: S01 E05 - Kelli & Randi | WOULD YOU HAND OVER THE WEDDING YOU'VE DREAMED OF… | Now this team has only seven days and five thousa… |  |  |
| r8 | For Better Or For Worse | For Better Or For Worse: S1 E6 - Jacqui & Chad | For Better Or For Worse: S01 E06 - Jacqui & Chad | What if you had no idea where, when or how you we… | Will these hardcore partiers turn a traditional c… |  |  |
| r9 | For Better Or For Worse | For Better Or For Worse: S1 E7 - Art & Janny | For Better Or For Worse: S01 E07 - Art & Janny | Everyone loves surprises, but what if you were ke… | Will this team see red when the planner suggests … |  |  |
| r10 | For Better Or For Worse | For Better Or For Worse: S1 E8 - Sasha & Eddie | For Better Or For Worse: S01 E08 - Sasha & Eddie | PULLING OFF THE PERFECT BEACH WEDDING IS HARD ENO… | Pulling off the perfect beach wedding is hard eno… |  |  |
| r11 | For Better Or For Worse | For Better Or For Worse: S1 E9 - Wendy & Michael | For Better Or For Worse: S01 E09 - Wendy & Michael | Trust is good, but would you trust a team of prac… | Trust is good, but would you trust a team of prac… |  |  |


### Try-load episodes: **0** rows parsed (with filters above if any)


---

## 10. `Stingray`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Pilot: Part 1 | 0 days 00:47:03 | 0_00 | A district attorney is kidnapped by a criminal wh… |
| r1 | Pilot: Part 2 | 0 days 00:48:38 | 0_01 | A district attorney is kidnapped by a criminal wh… |
| r2 | Ancient Eyes | 0 days 00:50:10 | 01_01 | Ray infiltrates an illegal migrant worker camp in… |
| r3 | Ether | 0 days 00:49:38 | 01_02 | Ray poses as a visiting surgeon to find out why a… |
| r4 | Below The Line | 0 days 00:49:46 | 01_03 | Ray is hired by an elementary school teacher to f… |
| r5 | Sometimes You Gotta Sing The Blues | 0 days 00:48:42 | 01_04 | Ray is picked up by the police and brought to the… |
| r6 | Abnormal Psych | 0 days 00:46:49 | 01_05 | When a young woman tries to kill Ray, and then st… |
| r7 | Orange Blossom | 0 days 00:49:33 | 01_06 | Ray is contacted by a doctor at a mental hospital… |
| r8 | Less Than The Eye Can See | 0 days 00:48:21 | 01_07 | An employee of WHO shows up at Ray's door, and pr… |
| r9 | That Terrible Swift Sword | 0 days 00:47:42 | 01_08 | Ray is hired by Sister Allison of a traveling rel… |
| r10 | The Greeter | 0 days 00:49:06 | 02_01 | A pharmaceutical chemist hires Ray to investigate… |
| r11 | Gemini | 0 days 00:48:10 | 02_02 | Someone from out of Ray's past is setting him up … |


### Try-load episodes: **0** rows parsed (with filters above if any)


---

## 11. `Carol Burnett - NOTE - EPISODE `

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `carol_burnett`

- **Name contains NOTE/Note:** yes — read tab instructions

- **Parser style (default → effective):** `carol_burnett`

- **YAML `nikki_row_filter`:** `green_episode_cell`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis |
| r1 | 021 - Dionne Warwick and Jonathan Winters | 01_19 | 1968-01-29 00:00:00 | ONLY | PLAY EPISODES IN GREEN |
| r2 | 003 - Jim Nabors | 01_01 | 1967-09-11 00:00:00 | Carol Burnett, Harvey Korman, Vicki Lawrence | Carol's series premiere guest is Jim Nabors. High… |
| r3 | 004 - Sid Caesar and Liza Minelli | 01_02 | 1967-09-18 00:00:00 | Carol Burnett, Harvey Korman, Vicki Lawrence | Highlights include: “Who’s Afraid Of Virginia Rob… |
| r4 | 005 - Eddie Albert and Jonathan Winters | 01_03 | 1967-09-25 00:00:00 | Carol Burnett, Harvey Korman, Vicki Lawrence | Carol brings out guest star Jonathan Winters duri… |
| r5 | 006 - Lucille Ball, Tim Conway and Gloria Loring | 01_04 | 1967-10-02 00:00:00 | Carol Burnett, Harvey Korman, Vicki Lawrence | Highlights include: two women (Carol and guest Lu… |
| r6 | 007 - Imogene Coca and Lainie Kazan | 01_05 | 1967-10-09 00:00:00 | Carol Burnett, Harvey Korman, Vicki Lawrence | Highlights include: Harvey attempts to ride a uni… |
| r7 | 008 - Phyllis Diller, Bobbie Gentry and Gwen Verdon | 01_06 | 1967-10-16 00:00:00 | Carol Burnett, Harvey Korman, Vicki Lawrence | Carol plays the wife of a monster in "Dr. Jekyll … |
| r8 | 009 - Diahann Carroll, Richard Kiley and The Smot… | 01_07 | 1967-10-23 00:00:00 | Carol Burnett, Harvey Korman, Vicki Lawrence | Highlights include: The Smothers Brothers doing a… |
| r9 | 011 - Nanette Fabray and Sonny & Cher | 01_08 | 1967-11-06 00:00:00 | Carol Burnett, Harvey Korman, Vicki Lawrence | Carol plays a dull secretary with a cold while sh… |
| r10 | 012 - Richard Chamberlain and Gloria Loring | 01_09 | 1967-11-13 00:00:00 | Carol Burnett, Harvey Korman, Vicki Lawrence | Highlights include: A “Gone With The Wind” parody… |
| r11 | 002 - With Juliet Prowse and Martha Raye | 01_10 | 1967-11-20 00:00:00 | Carol Burnett, Harvey Korman, Vicki Lawrence | Carol is Emily Pickett, a school teacher looking … |


### Try-load episodes: **104** rows parsed (with filters above if any)


---

## 12. `CPO Sharkey`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |
| r1 | Episode | Original Airdate | Stars | Synopsis | Notes |
| r2 | S1_EP01 - “Oh, Captain! My Captain” | 1976-12-01 00:00:00 | Don Rickles, Elizabeth Allen, Harrison Page | Sharkey reconsiders reenlisting when his new comm… |  |
| r3 | S1_EP02 - “Shimokawa Ships Out” | 1976-12-08 00:00:00 | Don Rickles, Elizabeth Allen, Harrison Page | Sharkey is accused of discrimination by a Japanes… |  |
| r4 | S1_EP03 - “The Dear John Letter” | 1976-12-22 00:00:00 | Don Rickles, Elizabeth Allen, Harrison Page | Sharkey tries to help a recruit write a break up … |  |
| r5 | S1_EP04 - “Goodbye, Dolly” | 1976-12-29 00:00:00 | Don Rickles, Elizabeth Allen, Harrison Page | The trainees have some free time and an inflatabl… |  |
| r6 | S1_EP05 - “Skolnick In Love” | 1977-01-12 00:00:00 | Don Rickles, Elizabeth Allen, Harrison Page | The shy Skolnick begins a whirlwind romance with … |  |
| r7 | S1_EP06 - “Mignone’s Mutiny” | 1977-01-19 00:00:00 | Don Rickles, Elizabeth Allen, Harrison Page | When Sharkey learns one of his recruits is using … |  |
| r8 | S1_EP07 - “Kowalski, The Somnambulist” | 1977-01-26 00:00:00 | Don Rickles, Elizabeth Allen, Harrison Page | Kowalski's sleepwalking leaves his facing a disch… |  |
| r9 | S1_EP08 - “Sunday In Tijuana” | 1977-02-09 00:00:00 | Don Rickles, Elizabeth Allen, Harrison Page | A trip to the Tijuana bullfights sees the recruit… |  |
| r10 | S1_EP09 - “Rodriguez And His Mamacita” | 1977-02-16 00:00:00 | Don Rickles, Elizabeth Allen, Harrison Page | The recruits try to hide Rodriguez's girlfriend a… |  |
| r11 | S1_EP10 - “Sharkey Boogies On Down” | 1977-02-23 00:00:00 | Don Rickles, Elizabeth Allen, Harrison Page | It's Sharkey's birthday and is disappointed that … |  |


### Try-load episodes: **0** rows parsed (with filters above if any)


---

## 13. `Date With The Angels`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis |
| r2 | High Fever | 01_03 | 1957-05-24 00:00:00 | Betty White, Bill Williams, Natalie Masters | Vickie insists that Gus receive medical treatment… |
| r3 | Wheel, The | 01_04 | 1957-05-31 00:00:00 | Betty White, Bill Williams, Jimmy Boyd | Vicki's teenage nephew sets the house on its ear. |
| r4 | Tree In The Parkway, The | 01_05 | 1957-06-07 00:00:00 | Betty White, Bill Williams, Nancy Kulp | Vickie gets the neighbors to sign a petition to s… |
| r5 | Feud, The | 01_06 | 1957-06-14 00:00:00 | Betty White, Bill Williams, Russell Hicks | Just before an expected visit from Gus' boss, Vic… |
| r6 | Shall We Dance? | 01_07 | 1957-06-21 00:00:00 | Betty White, Bill Williams, Richard Deacon | The Time: 8 months after Vickie and Gus were marr… |
| r7 | Blue Tie, The | 01_09 | 1957-07-12 00:00:00 | Betty White, Bill Williams, Hanley Stafford | Vicki goes to a department store to buy a gift fo… |
| r8 | Surprise, The | 01_11 | 1957-07-26 00:00:00 | Betty White, Bill Williams, Roy Engel | Gus has planned to surprise Vickie with a romanti… |
| r9 | Pike’s Pique | 01_12 | 1957-08-02 00:00:00 | Betty White, Bill Williams, Richard Reeves | The Time: 6 months after Vickie and Gus are marri… |
| r10 | Return Of The Wheel | 02_01 | 1957-09-06 00:00:00 | Betty White, Bill Williams, Jimmy Boyd | Vickie's destructive nephew Wheeler returns, havi… |
| r11 | Gorilla, The | 02_02 | 1957-09-13 00:00:00 | Betty White, Bill Williams, Roy Engel | The Angels are welcomed home from vacation by a g… |


### Try-load episodes: **22** rows parsed (with filters above if any)


---

## 14. `Dragnet - Dragnet`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Dragnet |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis |
| r2 | Big 22 Rifle | 02_07 | 1952-12-18 00:00:00 | Jack Webb, Herbert Ellis, William Johnstone | Friday and Smith search for a missing boy. The fi… |
| r3 | Big Bar | 04_08 | 1954-10-14 00:00:00 | Jack Webb, Ben Alexander, Walter Sande | A holdup man is sticking up bars. After he takes … |
| r4 | Big Betty | 03_04 | 1953-09-24 00:00:00 | Jack Webb, Ben Alexander, Gloria Saunders | A gang of con artists checks the obituary section… |
| r5 | Big Boys | 03_21 | 1954-01-21 00:00:00 | Jack Webb, Ben Alexander, Harry Bartell | Friday and Smith receive a bulletin about an arme… |
| r6 | Big Break | 02_19 | 1953-03-19 00:00:00 | Jack Webb, Ben Alexander, Clarence Cassell | Friday leads a team in a raid on the house of a v… |
| r7 | Big Crime | 04_03 | 1954-09-09 00:00:00 | Jack Webb, Ben Alexander, Jack Kruschen | When two four year old twin girls turn up missing… |
| r8 | Big False Make | 03_39 | 1954-05-27 00:00:00 | Jack Webb, Ben Alexander, Robert Crosson | Joe Friday interrogates a local gardener who's be… |
| r9 | Big Frame | 03_34 | 1954-04-22 00:00:00 | Jack Webb, Ben Alexander, Carolyn Jones | A man is found dead in the gutter. At first it se… |
| r10 | Big Girl | 03_31 | 1954-04-01 00:00:00 | Jack Webb, Ben Alexander, Art Gilmore | The detectives try to track down a tall, beautifu… |
| r11 | Big Grandma | 02_09 | 1953-01-08 00:00:00 | Jack Webb, Ben Alexander, Gwen Delano | Friday and Jacobs look for an elderly woman who h… |


### Try-load episodes: **32** rows parsed (with filters above if any)


---

## 15. `The Gene Autry Show`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis |
| r2 | Head For Texas | 01_01 | 1950-07-23 00:00:00 | Gene Autry, Champion, Pat Buttram | Gene faces trouble on two fronts when he befriend… |
| r3 | Gold Dust Charlie | 01_02 | 1950-07-30 00:00:00 | Gene Autry, Champion, Pat Buttram | When an old prospector is shot after making a ric… |
| r4 | Silver Arrow, The | 01_03 | 1950-08-06 00:00:00 | Gene Autry, Champion, Pat Buttram | Rodeo riders Gene Autry (Gene Autry) and Patrick … |
| r5 | Doodle Bug, The | 01_04 | 1950-08-13 00:00:00 | Gene Autry, Champion, Pat Buttram | While Gene Autry (Gene Autry) and his sidekick Pa… |
| r6 | Star Toter, The | 01_05 | 1950-08-20 00:00:00 | Gene Autry, Champion, Pat Buttram | Gene tries to reform the young son of an outlaw. … |
| r7 | Double Switch, The | 01_06 | 1950-08-27 00:00:00 | Gene Autry, Champion, Pat Buttram | When the state agrees to build a road if the coun… |
| r8 | Blackwater Valley Feud | 01_07 | 1950-09-03 00:00:00 | Gene Autry, Champion, Pat Buttram | A crook tries to grab two adjacent ranches owned … |
| r9 | Doublecross Valley | 01_08 | 1950-09-10 00:00:00 | Gene Autry, Champion, Pat Buttram | Gene investigates why a gang is trying so hard to… |
| r10 | Posse, The | 01_09 | 1950-09-17 00:00:00 | Gene Autry, Champion, Pat Buttram | An outlaw gang try to convince a former crook to … |
| r11 | Devil’s Brand, The | 01_10 | 1950-09-24 00:00:00 | Gene Autry, Champion, Pat Buttram | Foreman Gene Autry sends for the niece of his mur… |


### Try-load episodes: **91** rows parsed (with filters above if any)


---

## 16. `Greatest American Hero`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |  |
| r1 | Episode | Season/Episode | TRT | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | S01_E01 - The Greatest American Hero | 01_01 | 1:36:00 | 1981-03-18 00:00:00 | William Katt, Robert Culp, Connie Sellecca | The Pilot episode of the series. School teacher R… |  |
| r3 | S01_E02 - The Hit Car | 01_02 | 0:49:00 | 1981-03-25 00:00:00 | William Katt, Robert Culp, Connie Sellecca | Ralph's class prepares to perform Shakespeare whi… |  |
| r4 | S01_E03 - Here’s Looking At You, Kid | 01_03 | 1:00:00 | 1981-04-01 00:00:00 | William Katt, Robert Culp, Connie Sellecca | A military aircraft with a top-secret prototype t… |  |
| r5 | S01_E04 - Saturday Night On Sunset Boulevard | 01_04 | 0:49:00 | 1981-04-08 00:00:00 | William Katt, Robert Culp, Connie Sellecca | FBI agents and Russian killers pursue a man and w… |  |
| r6 | S01_E05 - Reseda Rose | 01_05 | 0:49:00 | 1981-04-15 00:00:00 | William Katt, Robert Culp, Connie Sellecca | Ralph and Pam's plans (all of them) take a back s… |  |
| r7 | S01_E06 - My Heroes Have Always Been Cowboys | 01_06 | 0:50:00 | 1981-04-29 00:00:00 | William Katt, Robert Culp, Connie Sellecca | Ralph retires the suit after his super-heroics re… |  |
| r8 | S01_E07 - Fire Man | 01_07 | 0:50:00 | 1981-05-06 00:00:00 | William Katt, Robert Culp, Connie Sellecca | Tony is accused of arson, and Bill and Ralph must… |  |
| r9 | S01_E08 - The Best Desk Scenario | 01_08 | 0:49:00 | 1981-05-13 00:00:00 | William Katt, Robert Culp, Connie Sellecca | Pam and Ralph get promotions, and Bill begins to … |  |
| r10 | S02_E01 - The Two-Hundred-Mile-An-Hour Fast Ball | 02_01 | 0:50:00 | 1981-11-04 00:00:00 | William Katt, Robert Culp, Connie Sellecca | Crooks needing cash to swing an arms deal bet hea… |  |
| r11 | S02_E02 - Operation Spoilsport | 02_02 | 0:50:00 | 1981-11-11 00:00:00 | William Katt, Robert Culp, Connie Sellecca | The aliens return and tell Ralph and Bill that th… |  |


### Try-load episodes: **43** rows parsed (with filters above if any)


---

## 17. `The Life & Legend of Wyatt Earp`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | The Life And Legend Of Wyatt Earp |  |  |  |  |  |
| r1 | Episode | Season/Episode |  |  |  |  |
| r2 | 101_Wyatt Earp Becomes A Marshal | 01_01 |  |  |  |  |
| r3 | 102_Mr. Earp Meets A Lady | 01_02 |  |  |  |  |
| r4 | 103_Bill Thompson Gives In | 01_03 |  |  |  |  |
| r5 | 104 - Marshal Earp Meets General Lee | 01_04 |  |  |  |  |
| r6 | 105_Wyatt Earp Comes to Wichita | 01_05 |  |  |  |  |
| r7 | 106_The Man Who Lied | 01_06 |  |  |  |  |
| r8 | 107_The Gambler | 01_07 |  |  |  |  |
| r9 | 108_The Killer | 01_08 |  |  |  |  |
| r10 | 109_John Wesley Hardin | 01_09 |  |  |  |  |
| r11 | 110_The Bank Robbers | 01_10 |  |  |  |  |


### Try-load episodes: **226** rows parsed (with filters above if any)


---

## 18. `Hawkeye (color)`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |
| r1 | Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | Hawkeye Prequel Pilot: Part 1 | 1994-09-18 00:00:00 | Lee Horsley, Lynda Carter, Rodney A. Grant | British Captain Taylor Shields' brother William a… |  |
| r3 | Hawkeye Pilot: Part 2 | 1994-09-25 00:00:00 | Lee Horsley, Lynda Carter, Rodney A. Grant | Captain Taylor enlists two ne'er do wells to help… |  |
| r4 | Bear, The | 1994-10-02 00:00:00 | Lee Horsley, Lynda Carter, Rodney A. Grant | Elizabeth picks berries in the woods, but is frig… |  |
| r5 | Furlough, The | 1994-10-09 00:00:00 | Lee Horsley, Lynda Carter, Rodney A. Grant | Young widow Sarah Pritchard is rescued from a lec… |  |
| r6 | Siege, The | 1994-10-16 00:00:00 | Lee Horsley, Lynda Carter, Rodney A. Grant | The French are laying siege to the fort. Rumor co… |  |
| r7 | Child, The | 1994-10-23 00:00:00 | Lee Horsley, Lynda Carter, Rodney A. Grant | A couple from Virginia with a child seek safety i… |  |
| r8 | Vision, The | 1994-11-06 00:00:00 | Lee Horsley, Lynda Carter, Rodney A. Grant | Chingachgook has a vision where in defense of Eli… |  |
| r9 | Out Of The Past | 1994-11-13 00:00:00 | Lee Horsley, Lynda Carter, Rodney A. Grant | An old friend of Hawkeye's shows up just after tw… |  |
| r10 | Warrior, The | 1994-11-20 00:00:00 | Lee Horsley, Lynda Carter, Rodney A. Grant | On the way to visit his aunt Elizabeth, young And… |  |
| r11 | Quest, The | 1994-11-27 00:00:00 | Lee Horsley, Lynda Carter, Rodney A. Grant | Elizabeth, Hawkeye and Taylor go on a quest to fo… |  |


### Try-load episodes: **0** rows parsed (with filters above if any)


---

## 19. `Hunter`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `hunter`

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `hunter`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | HUN_101 - Hunter | 01_01 | 1984-09-18 00:00:00 | Fred Dryer, Stepfanie Kramer, Brian Dennehy | Brash detectives Rick Hunter & Dee Dee McCall tea… |  |
| r3 | HUN_102 - Hard Contract | 01_02 | 1984-09-28 00:00:00 | Fred Dryer, Stepfanie Kramer, David Ackroyd | Hunter & McCall make a pact of protectiveness and… |  |
| r4 | HUN_103 - The Hot Grounder | 01_03 | 1984-10-05 00:00:00 | Fred Dryer, Stepfanie Kramer, William Windom | When the wife of the commissioner is killed in ca… |  |
| r5 | HUN_104 - A Long Way From L.A. | 01_04 | 1984-10-26 00:00:00 | Fred Dryer, Stepfanie Kramer, Bo Svenson | Hunter and McCall are transporting a prisoner bac… |  |
| r6 | HUN_105 - Legacy | 01_05 | 1984-11-02 00:00:00 | Fred Dryer, Stepfanie Kramer, Vincent Baggetta | When a mobster is killed, Hunter who knew the man… |  |
| r7 | HUN_106 - Flight On A Dead Pigeon | 01_06 | 1984-11-09 00:00:00 | Fred Dryer, Stepfanie Kramer, Marissa Mendenhall | Hunter and McCall try to help a young girl whose … |  |
| r8 | HUN_107 - Pen Pals | 01_07 | 1984-11-16 00:00:00 | Fred Dryer, Stepfanie Kramer, Tim Thomerson | Hunter does not receive a warm welcome when he is… |  |
| r9 | HUN_108 - Dead Or Alive | 01_08 | 1984-11-30 00:00:00 | Fred Dryer, Stepfanie Kramer, Wings Hauser | Jimmie Joe Walker is a bounty hunter that has com… |  |
| r10 | HUN_109 - High Bleacher Man | 01_09 | 1984-12-07 00:00:00 | Fred Dryer, Stepfanie Kramer, Michael Baseleon | Hunter and McCall apprehend Gavin, a murdering st… |  |
| r11 | HUN_110 - The Shooter | 01_10 | 1985-01-04 00:00:00 | Fred Dryer, Stepfanie Kramer, Robert Dryer | At the scene of a crime Hunter finds the cigarett… |  |


### Try-load episodes: **152** rows parsed (with filters above if any)


---

## 20. `Laugh-In - NOTE - CC Files are `

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `laugh_in`

- **Name contains NOTE/Note:** yes — read tab instructions

- **Parser style (default → effective):** `laugh_in`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Episode | TRT | Color/B&W | Season/Episode | Year/Original Airdate | Stars | Synopsis |
| r1 | S1_E00 - Pilot | 0:57:42 | Color | 01_00 | 1967-09-09 00:00:00 | Dan Rowan, Dick Martin, Pamela Austin | Dan Rowan and Dick Martin host a Laugh-In. Along … |
| r2 | S1_E01 - Premiere - Barbara Feldon, Flip Wilson, … | 0:52:35 | Color | 01_01 | 1968-01-22 00:00:00 | Dan Rowan, Dick Martin, Pamela Austin | Tiny Tim makes his network television debut and t… |
| r3 | S1_E02 - Robert Culp, Flip Wilson, The First Edit… | 0:52:31 | Color | 01_02 | 1968-01-29 00:00:00 | Dan Rowan, Dick Martin, Robert Culp | Sketches include News of the past, present, and t… |
| r4 | S1_E03 - Tim Conway, Cher, Lorne Greene, Sheldon … | 0:52:35 | Color | 01_03 | 1968-02-05 00:00:00 | Dan Rowan, Dick Martin, Tim Conway | First appearance of Goldie Hawn as a "Regular Per… |
| r5 | S1_E04 - Pamela Austin, Don Adams, The Nitty Grit… | 0:52:31 | Color | 01_04 | 1968-02-12 00:00:00 | Dan Rowan, Dick Martin, Pamela Austin | Sketches include Maude's World of medicine, Hospi… |
| r6 | S1_E05 - Dinah Shore, Walter Slezak, Peter Lawfor… | 0:52:23 | Color | 01_05 | 1968-02-19 00:00:00 | Dan Rowan, Dick Martin, Pamela Austin | Maude's World of Fashion and Glamour, Cocktail Pa… |
| r7 | S1_E06 - Larry Storch, Connie Stevens, Nancy Ames… | 0:52:23 | Color | 01_06 | 1968-02-26 00:00:00 | Dan Rowan, Dick Martin, Larry Storch | Mod, Mod World looks at vacations. |
| r8 | S1_E07 - Sally Field, Terry-Thomas, Joby Baker, G… | 0:52:23 | Color | 01_07 | 1968-03-04 00:00:00 | Dan Rowan, Dick Martin, Sally Field | Terry-Thomas impersonates Moses presenting the ne… |
| r9 | S1_E08 - Barbara Feldon, Sonny Bono, Cher, Pat Mo… | 0:52:15 | Color | 01_08 | 1968-03-11 00:00:00 | Dan Rowan, Dick Martin, Barbara Feldon | Laugh-In salutes the Hereafter and George Wallace. |
| r10 | S1_E09 - Joey Bishop, Sammy Davis, Jr. | 0:52:34 | Color | 01_09 | 1968-03-25 00:00:00 | Dan Rowan, Dick Martin, Joey Bishop | Laugh-In salutes the Olympics. |
| r11 | S1_E10 - Barbara Feldon, Flip Wilson, The Bee Gees | 0:52:24 | Color | 01_10 | 1968-04-01 00:00:00 | Dan Rowan, Dick Martin, Barbara Feldon | Mod, Mod World looks at communication. |


### Try-load episodes: **141** rows parsed (with filters above if any)


---

## 21. `SHERLOCK HOLMES`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Display Title (EXTERNAL) |  | Table 1 |  |  |  |  |
| r1 | The Adventures Of Sherlock Holmes |  | Episode | TRT | Color/B&W | CC | Season/Episode |
| r2 | The Adventures Of Sherlock Holmes: Season 1 |  | Series 01 - The Adventures Of Sherlock Holmes - 0… | 0:52:05 | Color | scc | Series01_01_01 |
| r3 | The Adventures Of Sherlock Holmes: S1 E1 - A Scan… |  | Series 01 - The Adventures Of Sherlock Holmes - 0… | 0:52:02 | Color | scc | Series01_01_02 |
| r4 | The Adventures Of Sherlock Holmes: S1 E2 - The Da… |  | Series 01 - The Adventures Of Sherlock Holmes - 0… | 0:52:05 | Color | scc | Series01_01_03 |
| r5 | The Adventures Of Sherlock Holmes: S1 E3 - The Na… |  | Series 01 - The Adventures Of Sherlock Holmes - 0… | 0:52:02 | Color | scc | Series01_01_04 |
| r6 | The Adventures Of Sherlock Holmes: S1 E4 - The So… |  | Series 01 - The Adventures Of Sherlock Holmes - 0… | 0:51:35 | Color | scc | Series01_01_05 |
| r7 | The Adventures Of Sherlock Holmes: S1 E5 - The Cr… |  | Series 01 - The Adventures Of Sherlock Holmes - 0… | 0:52:32 | Color | scc | Series01_01_06 |
| r8 | The Adventures Of Sherlock Holmes: S1 E6 - The Sp… |  | Series 01 - The Adventures Of Sherlock Holmes - 0… | 0:51:52 | Color | scc | Series01_01_07 |
| r9 | The Adventures Of Sherlock Holmes: S1 E7 - The Bl… |  | Series 01 - The Adventures Of Sherlock Holmes - 0… | 0:51:13 | Color | scc | Series01_02_01 |
| r10 | The Adventures Of Sherlock Holmes: Season 2 |  | Series 01 - The Adventures Of Sherlock Holmes - 0… | 0:50:25 | Color | scc | Series01_02_02 |
| r11 | The Adventures Of Sherlock Holmes: S2 E1 - The Co… |  | Series 01 - The Adventures Of Sherlock Holmes - 1… | 0:52:07 | Color | scc | Series01_02_03 |


### Try-load episodes: **41** rows parsed (with filters above if any)


---

## 22. `Jack Benny Program`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Original Airdate | Stars | Synopsis | Notes |
| r2 | Premiere Show | 01_01 | 1950-10-28 00:00:00 | Jack Benny, Eddie ‘Rochester’ Anderson, Don Wilson | Benny's first program drives the studio audience … |  |
| r3 | Dorothy Shay | 02_01 | 1951-11-04 00:00:00 | Jack Benny, Dorothy Shay, Frank Remley | While doing the opening monologue for his show, J… |  |
| r4 | Gaslight | 02_03 | 1952-01-27 00:00:00 | Jack Benny, Eddie ‘Rochester’ Anderson, Don Wilson | In a spoof of the movie, Gaslight, Jack portrays … |  |
| r5 | Jack Gets Robbed | 03_03 | 1952-11-30 00:00:00 | Jack Benny, Bob Crosby, Eddie ‘Rochester’ Anderson | Jack is pestered by a young autograph seeker, the… |  |
| r6 | Fred Allen Show | 03_07 | 1953-04-19 00:00:00 | Jack Benny, Eddie ‘Rochester’ Anderson, Don Wilson | Fred does his best to get Jack fired by the spons… |  |
| r7 | Jack Visits The Vault | 03_08 | 1953-05-17 00:00:00 | Jack Benny, Eddie ‘Rochester’ Anderson, Don Wilson |  |  |
| r8 | Honolulu Trip | 04_01 | 1953-09-13 00:00:00 | Jack Benny, Eddie ‘Rochester’ Anderson, Don Wilson | Jack and Rochester are returning from a vacation … |  |
| r9 | Jack As A Child | 04_02 | 1953-10-04 00:00:00 | Jack Benny, Eddie ‘Rochester’ Anderson, Don Wilson |  |  |
| r10 | Humphrey Bogart Show | 04_03 | 1953-10-25 00:00:00 | Jack Benny, Humphrey Bogart, Bob Crosby | Police Lt. Jack Benny questions notorious killer … |  |
| r11 | Johnnie Ray Show | 04_04 | 1953-11-15 00:00:00 | Jack Benny, Johnnie Ray, Eddie ‘Rochester’ Anderson | Johnnie Ray's contract to appear on Benny's TV sh… |  |


### Try-load episodes: **159** rows parsed (with filters above if any)


---

## 23. `FARSCAPE`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Farscape | Thrown into a distant part of the universe, an Ea… |
| r1 | Farscape: Season 1 | Thrown into a distant part of the universe, an Ea… |
| r2 | Farscape: S1 E1 - Premiere | Astronaut John Crichton attempts to use the Earth… |
| r3 | Farscape: S1 E2 - Exodus From Genesis | A locator beacon, automatically broadcasting its … |
| r4 | Farscape: S1 E3 - Back And Back And Back To The F… | The crew rescues a scientist and his assistant fr… |
| r5 | Farscape: S1 E4 - Throne For A Loss | Rygel is captured and held for ransom by some bou… |
| r6 | Farscape: S1 E5 - PK Tech Girl | After finding the legendary Peacekeeper battleshi… |
| r7 | Farscape: S1 E6 - Thank God It's Friday, Again | The crew visits a planet full of happy workers. S… |
| r8 | Farscape: S1 E7 - I, E.T. | A peacekeeper beacon goes off and Moya has to lan… |
| r9 | Farscape: S1 E8 - That Old Black Magic | Crichton's spirit is captured by Maldis. The sorc… |
| r10 | Farscape: S1 E9 - DNA Mad Scientist | A scientist extracts DNA from several of Moya's c… |
| r11 | Farscape: S1 E10 - They've Got A Secret | During routine searches for Peacekeeper beacons, … |


### Try-load episodes: **0** rows parsed (with filters above if any)


---

## 24. `CANDID CAMERA`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |
| r1 | Episode | Synopsis |
| r2 | 10001 | The CBS premiere episode in October 1960. |
| r3 | 10002 | Yankees stars Mickey Mantle and Yogi Berra find s… |
| r4 | 10041 | Supermarket carts go crooked.  With guest Zsa Zsa… |
| r5 | 10042 | Allen Funt and crew make an historic journey to M… |
| r6 | 10045 | A golf course has missing holes. |
| r7 | 10060 | Loud eating noises and a flying phone booth. |
| r8 | 10061 | A dribble glass and dancing traffic cops. |
| r9 | 10073 | Guest Wally Cox tries to get longshoremen to diet. |
| r10 | 10082 | A kangaroo bounces into a gas station. |
| r11 | 10087 | Trying to get money from under a tire. |


### Try-load episodes: **0** rows parsed (with filters above if any)


---

## 25. `Life With Elizabeth`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis |
| r2 | Bad Mood - First Kiss - Ex-Flame | 01_00 | 1953 | Betty White, Del Moore, Hal March | Three separate stories in the life of our two pro… |
| r3 | Black Eye - Momma Breakfast - Missing Receptionist |  |  | Robert Emlin, Ray Erlenborn, Del Moore | Elizabeth gives herself a shiner the same evening… |
| r4 | Bonus Check - House Cleaning - Richard’s Mistake |  |  | Betty White, Del Moore, Dick Garton | In the first vignette, Elizabeth and Alvin are pl… |
| r5 | Car Stolen - Fence Painting - Real Estate |  | 1953 | Betty White, Del Moore, Dick Garton | In the first story, Elizabeth must tell Alvin the… |
| r6 | Carpentry - Hypnotism - Home Movies |  |  |  |  |
| r7 | Check Book - Late Party - Piano Tuner |  |  |  |  |
| r8 | Collection Agency - Monster Green Eyes - Good Nei… |  | 1954 | Betty White, Del, Moore, Joe Cranston | A notice about an overdue bill concerns Elizabeth… |
| r9 | Day Off - Varnishing Floor - Singing Lesson |  |  |  |  |
| r10 | Detective Story - Writing A Speech - Moosie On Patio |  |  | Betty White, Del Moore, LeRoy Lennart | 1) Elizabeth and company get involved in some det… |
| r11 | Everything Goes Wrong - Kind To Animals - Babysit… |  |  | Betty White, Del Moore, Scotty Beckett | 1) Elizabeth sustains a lot of minor injuries. 2)… |


### Try-load episodes: **27** rows parsed (with filters above if any)


---

## 26. `Lucy Show`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `lucy`

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic` + YAML override `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |
| r1 | Episode | Season/Episode | Original Airdate | Stars | Synopsis |
| r2 | Lucy And Viv Put In A Shower | 01_18 | 1963-01-28 00:00:00 | Lucille Ball, Vivian Vance, Dick Martin | After Lucy drives off the plumber with her meddli… |
| r3 | Lucy’s Barbershop Quartet | 01_19 | 1963-02-04 00:00:00 | Lucille Ball, Vivian Vance, Hans Conried | When one of the members of Viv's female barbersho… |
| r4 | Lucy With George Burns | 05_01 | 1966-09-12 00:00:00 | Lucille Ball, Gale Gordon, George Burns | When visiting the bank as a customer, George Burn… |
| r5 | Lucy And The Submarine | 05_02 | 1966-09-19 00:00:00 | Lucille Ball, Gale Gordon, Roy Roberts | Mr. Mooney leaves the office for two weeks of tra… |
| r6 | Lucy The Bean Queen | 05_03 | 1967-09-26 00:00:00 | Lucille Ball, Gale Gordon, Ed Begley | When Mr. Mooney refuses to co-sign Lucy's loan fo… |
| r7 | Lucy And Paul Winchell | 05_04 | 1966-10-03 00:00:00 | Lucille Ball, Gale Gordon, Paul Winchell | Lucy arranges for ventriloquist Paul Winchell to … |
| r8 | Lucy And The Ring-A-Ding Ring | 05_05 | 1966-10-10 00:00:00 | Lucille Ball, Gale Gordon, Mary Jane Croft | Lucy tries on an expensive ring Mr. Mooney had ma… |
| r9 | Lucy Flies To London | 05_06 | 1966-10-17 00:00:00 | Lucille Ball, Gale Gordon, Mary Jane Croft | Lucy enters a dog food jingle contest and wins th… |
| r10 | Lucy Gets A Roommate | 05_07 | 1966-10-31 00:00:00 | Lucille Ball, Gale Gordon, Carol Burnett | In order to cut down on expenses, Lucy advertises… |
| r11 | Lucy And Carol In Palm Springs | 05_08 | 1966-11-07 00:00:00 | Lucille Ball, Gale Gordon, Carol Burnett | Lucy calls in sick so she can join her roommate a… |


### Try-load episodes: **30** rows parsed (with filters above if any)


---

## 27. `MST3K - NOTE - Each episode fol`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `mst3k`

- **Name contains NOTE/Note:** yes — read tab instructions

- **Parser style (default → effective):** `mst3k`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | NOTE - Each episode folder contains the episode a… |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | Attack Of The Giant Leeches | 05_06 | 1992-07-18 00:00:00 | Trace Beaulieu, Joel Hodgson, Jim Mallon | Joel and the 'bots get water on the brain after a… | SCC file contained in same folder as movie  Copy … |
| r3 | Beatniks, The | 05_15 | 1992-11-26 00:00:00 | Trace Beaulieu, Joel Hodgson, Jim Mallon | Joel and the Bots watch a second segment from an … | SCC file contained in same folder as movie  Copy … |
| r4 | Cave Dwellers | 04_01 | 1991-06-01 00:00:00 | Trace Beaulieu, Joel Hodgson, Jim Mallon | Joel and the Bots endure Miles O'Keeffe as Ator w… | SCC file contained in same folder as movie  Copy … |
| r5 | Code Name Diamond Head | 07_08 | 1994-10-01 00:00:00 | Trace Beaulieu, Michael J. Nelson, Jim Mallon | A down-home country family eat apple pie and rais… | SCC file contained in same folder as movie  Copy … |
| r6 | Crash Of The Moons | 05_17 | 1992-11-28 00:00:00 | Trace Beaulieu, Joel Hodgson, Jim Mallon | The crew pokes fun at another segment of a 1960s … | SCC file contained in same folder as movie  Copy … |
| r7 | Eegah | 06_06 | 1993-08-28 00:00:00 | Trace Beaulieu, Joel Hodgson, Jim Mallon | A teenage girl, her dorky boyfriend, and her scie… | SCC file contained in same folder as movie  Copy … |
| r8 | First Spaceship On Venus | 03_11 | 1990-12-29 00:00:00 | Trace Beaulieu, Joel Hodgson, Jim Mallon | Joel and the 'bots suffer through First Spaceship… | SCC file contained in same folder as movie  Copy … |
| r9 | Fugitive Alien | 04_10 | 1991-08-17 00:00:00 | Trace Beaulieu, Joel Hodgson, Jim Mallon | Joel and the Bots watch as an alien named Ken joi… | SCC file contained in same folder as movie  Copy … |
| r10 | Fugitive Alien 2 | 04_18 | 1991-11-16 00:00:00 | Trace Beaulieu, Joel Hodgson, Jim Mallon | Ken and the crew of the Bacchus 3 return in Star … | IMDB Title - Star Force: Fugitive Alien II  SCC f… |
| r11 | Hercules | 06_02 | 1993-06-17 00:00:00 | Trace Beaulieu, Joel Hodgson, Jim Mallon | Joel and the Bots have a casual day on the SOL an… | SCC file contained in same folder as movie  Copy … |


### Try-load episodes: **41** rows parsed (with filters above if any)


---

## 28. `My Little Margie`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | Reverse Psychology | 01_00 | 1952-06-09 00:00:00 | Gale Storm, Charles Farrell, Hillary Brooke | Father Vern and his grown daughter Margie can't r… |  |
| r3 | Friend For Roberta | 01_01 | 1952-06-16 00:00:00 | Gale Storm, Charles Farrell, Hillary Brooke | Worried that Roberta is comprising Vern's time an… |  |
| r4 | Radioactive Margie | 01_02 | 1952-06-23 00:00:00 | Gale Storm, Charles Farrell, Don Hayden | Margie writes a fake letter saying there is urani… |  |
| r5 | Margie Sings Opera | 01_03 | 1952-06-30 00:00:00 | Gale Storm, Charles Farrell, Clarence Kolb | Margie's friend, Ginny has plans and can't meet u… |  |
| r6 | Margie’s Sister Sally | 01_04 | 1952-07-07 00:00:00 | Gale Storm, Charles Farrell, Ron Randell | To help her father Vern with a client Margie agre… |  |
| r7 | Costume Party | 01_05 | 1952-07-14 00:00:00 | Gale Storm, Charles Farrell, Hillary Brooke | Margie and Honeywell use the attendance of a riva… |  |
| r8 | Margie Plays Detective | 01_06 | 1952-07-21 00:00:00 | Gale Storm, Charles Farrell, Hillary Brooke | Margie and boyfriend Freddie try to find out who … |  |
| r9 | Insurance | 01_07 | 1952-07-28 00:00:00 | Gale Storm, Charles Farrell, Clarence Kolb | Margie falls under the impression that her father… |  |
| r10 | Margie’s Mink | 01_08 | 1952-08-11 00:00:00 | Gale Storm, Charles Farrell, Clarence Kolb | When Margie receives a mink instead of what she r… |  |
| r11 | Efficiency Expert | 01_09 | 1952-08-18 00:00:00 | Gale Storm, Charles Farrell, Hillary Brooke | To show Vern Freddie is not so objectionable, Mar… |  |


### Try-load episodes: **93** rows parsed (with filters above if any)


---

## 29. `Petticoat Junction`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | 101_Spur Line To Shady Rest | 01_01 | 1963-09-24 00:00:00 | Bea Benaderet, Edgar Buchanan, Jeannine Riley | The struggling Shady Rest Hotel is further jeopar… |  |
| r3 | 102_Quick, Hide The Railroad | 01_02 | 1963-10-01 00:00:00 | Bea Benaderet, Edgar Buchanan, Jeannine Riley | Kate uses a combination of charm, subterfuge, and… |  |
| r4 | 103_The President Who Came To Dinner | 01_03 | 1963-10-08 00:00:00 | Bea Benaderet, Edgar Buchanan, Jeannine Riley | Hard-hitting railroad president Norman Curtis tra… |  |
| r5 | 104_Is There A Doctor In The Roundhouse? | 01_04 | 1963-10-15 00:00:00 | Bea Benaderet, Edgar Buchanan, Jeannine Riley | The Shady Rest's Annual Jamboree is threatened wh… |  |
| r6 | 105_Courtship Of Floyd Smoot | 01_05 | 1963-10-22 00:00:00 | Bea Benaderet, Edgar Buchanan, Jeannine Riley | Floyd Smoot, the conductor, is courting a woman t… |  |
| r7 | 106_Please Buy Me Violets | 01_06 | 1963-10-29 00:00:00 | Bea Benaderet, Edgar Buchanan, Jeannine Riley | Uncle Joe spends Kate's money to buy cases of lou… |  |
| r8 | 107_The Ringer | 01_07 | 1963-11-05 00:00:00 | Bea Benaderet, Edgar Buchanan, Jeannine Riley | Athletic Betty Jo becomes the first-ever female e… |  |
| r9 | 108_Kate’s Recipe For Hot Rhubarb | 01_08 | 1963-11-12 00:00:00 | Bea Benaderet, Edgar Buchanan, Jeannine Riley | When Kate talks Bobbie Jo into going on a double … |  |
| r10 | 109_The Little Train Robbery | 01_09 | 1963-11-19 00:00:00 | Bea Benaderet, Edgar Buchanan, Jeannine Riley | Two young men - opinionated Arthur Gilroy and his… |  |
| r11 | 110_Bedloe Strikes Again | 01_10 | 1963-11-26 00:00:00 | Bea Benaderet, Edgar Buchanan, Jeannine Riley | The Cannonball and its primary passenger, Uncle J… |  |


### Try-load episodes: **20** rows parsed (with filters above if any)


---

## 30. `ozzie and harriet`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r1 | Episode | Season/Episode | Original Airdate | Stars | Synopsis |
| r2 | 01_01 - The Rivals | 01_01 | 1952-10-03 00:00:00 | Ozzie Nelson, Harriet Nelson, David Nelson | David has a rival, and his name is Will Thornberr… |
| r3 | 01_02 - The Poet | 01_02 | 1952-10-10 00:00:00 | Ozzie Nelson, Harriet Nelson, David Nelson | Ozzie and Harriet read the newspaper and talk abo… |
| r4 | 01_03 - The Pills | 01_03 | 1952-10-17 00:00:00 | Ozzie Nelson, Harriet Nelson, David Nelson | Ozzie decides to diet so he can fit into a pair o… |
| r5 | 01_04 - The Fall Guy | 01_04 | 1952-10-24 00:00:00 | Ozzie Nelson, Harriet Nelson, David Nelson | Ozzie quickly regrets advising David against allo… |
| r6 | 01_05 - Halloween Party | 01_05 | 1952-10-31 00:00:00 | Ozzie Nelson, Harriet Nelson, David Nelson | On Halloween night, Ozzie and Thorny make plans t… |
| r7 | 01_06 - Riviera Ballet | 01_06 | 1952-11-07 00:00:00 | Ozzie Nelson, Harriet Nelson, David Nelson | Ozzie has tickets to the Riviera Ballet, but Harr… |
| r8 | 01_07 - David The Babysitter | 01_07 | 1952-11-14 00:00:00 | Ozzie Nelson, Harriet Nelson, David Nelson | David gets a babysitting job and Ozzie is worried… |
| r9 | 01_08 - Ricky Goes To A Dance | 01_08 | 1952-11-21 00:00:00 | Ozzie Nelson, Harriet Nelson, David Nelson | Ricky receives a perfumed letter from his neighbo… |
| r10 | 01_09 - Day After Thanksgiving | 01_09 | 1952-11-28 00:00:00 | Ozzie Nelson, Harriet Nelson, David Nelson | Having come home the previous day from Aunt Ellen… |
| r11 | 01_10 - Thorny’s Gift | 01_10 | 1952-12-05 00:00:00 | Ozzie Nelson, Harriet Nelson, David Nelson | Ozzie is outraged after he doesn't receive a time… |


### Try-load episodes: **435** rows parsed (with filters above if any)


---

## 31. `Real McCoys - NOTE - Each Seaso`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `real_mccoys`

- **Name contains NOTE/Note:** yes — read tab instructions

- **Parser style (default → effective):** `real_mccoys`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | NOTE - Each Season contains caption, h264, marker… |  |  |  |  |  |  |
| r1 | Episode | TRT | Color/B&W | Season/Episode | Original Airdate | Stars | Synopsis |
| r2 | 101 - Californy, Here We Come | 0:24:55 | B/W | 01_01 | 1957-10-03 00:00:00 | Walter Brennan, Richard Crenna, Kathleen Nolan | Grandpa, Luke, Kate, Hassie and Little Luke McCoy… |
| r3 | 102 - The Egg War | 0:22:23 | B/W | 01_02 | 1957-10-10 00:00:00 | Walter Brennan, Richard Crenna, Kathleen Nolan | Grandpa gets into an egg feud with a rival egg sa… |
| r4 | 103 - Kate’s Dress | 0:22:23 | B/W | 01_03 | 1957-10-17 00:00:00 | Walter Brennan, Richard Crenna, Kathleen Nolan | Grandpa and Luke need a new gun for a shooting co… |
| r5 | 104 - Grandpa Sells His Gun | 0:22:15 | B/W | 01_04 | 1957-10-24 00:00:00 | Walter Brennan, Richard Crenna, Kathleen Nolan | The McCoys find out that they are three months be… |
| r6 | 105 - A Question Of Discipline | 0:22:22 | B/W | 01_05 | 1957-10-31 00:00:00 | Walter Brennan, Richard Crenna, Kathleen Nolan | Kate wants to discipline Hassie and Little Luke f… |
| r7 | 106 - You Can’t Cheat An Honest Man | 0:22:24 | B/W | 01_06 | 1957-11-07 00:00:00 | Walter Brennan, Richard Crenna, Kathleen Nolan | Grandpa's innate honesty saves the day when a dis… |
| r8 | 107 - Luke Gets His Freedom | 0:22:13 | B/W | 01_07 | 1957-11-14 00:00:00 | Walter Brennan, Richard Crenna, Kathleen Nolan | Kate pointedly tells Luke that he is welcome to g… |
| r9 | 108 - Grandpa’s Date | 0:22:25 | B/W | 01_08 | 1957-11-21 00:00:00 | Walter Brennan, Richard Crenna, Kathleen Nolan | The Farmer's Association is having it's fall danc… |
| r10 | 109 - The Fishing Contest | 0:22:19 | B/W | 01_09 | 1957-11-28 00:00:00 | Walter Brennan, Richard Crenna, Kathleen Nolan | Grandpa and George MacMichael compete to win the … |
| r11 | 110 - It’s A Woman’s World | 0:22:21 | B/W | 01_10 | 1957-12-05 00:00:00 | Walter Brennan, Richard Crenna, Kathleen Nolan | Grandpa pretends to be able to read so he can vot… |


### Try-load episodes: **223** rows parsed (with filters above if any)


---

## 32. `The Saint - NOTE - Episode titl`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `saint`

- **Name contains NOTE/Note:** yes — read tab instructions

- **Parser style (default → effective):** `saint`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | NOTE - Episode titles in red are not in-house and… |  |  |  |  |  |  |
| r1 | Episode | Shout Factory Numbering | B&W / Color | Season/Episode | Year/Original Airdate | Stars | Synopsis |
| r2 | S01_E01 - The Talented Husband | 6141619 | B&W | 01_01 | 1962-10-04 00:00:00 | Roger Moore, Derek Farr, Shirley Eaton | Simon finds himself with a glamorous partner when… |
| r3 | S01_E02 - The Latin Touch | 6141620 | B&W | 01_02 | 1962-10-11 00:00:00 | Roger Moore, Alexander Knox, Doris Nolan | Simon goes to help a young American woman who's b… |
| r4 | S01_E03 - The Careful Tourist | 2254979 | B&W | 01_03 | 1962-10-18 00:00:00 | Roger Moore, David Kossoff, Peter Dyneley | A reporter friend of Simon's is callously murdere… |
| r5 | S01_E04 - The Covetous Headsman | 2254975 | B&W | 01_04 | 1962-10-25 00:00:00 | Roger Moore, Barbara Shelley, Eugene Deckers | Simon meets a young woman on a plane - and flies … |
| r6 | S01_E05 - The Loaded Tourist | 6141621 | B&W | 01_05 | 1962-11-01 00:00:00 | Roger Moore, Barbara Bates, Edward Evans | Simon witnesses a murder and finds himself in the… |
| r7 | S01_E06 - The Pearls Of Peace | 6141623 | B&W | 01_06 | 1962-11-08 00:00:00 | Roger Moore, Dina Paisner, Erica Rogers | Simon helps subsidise a man's dream of adventure … |
| r8 | S01_E07 - The Arrow Of God | 2322154 | B&W | 01_07 | 1962-11-15 00:00:00 | Roger Moore, Elspeth March, Ronald Leigh-Hunt | A slimy gossip columnist is killed and it's up to… |
| r9 | S01_E08 - The Element Of Doubt | 2322160 | B&W | 01_08 | 1962-11-22 00:00:00 | Roger Moore, David Bauer, Alan Gifford | Simon settles an account with a corrupt American … |
| r10 | S01_E09 - The Effete Angler | 2321437 | B&W | 01_09 | 1962-11-29 00:00:00 | Roger Moore, Shirley Eaton, George Pravda | Simon goes fishing with a glamorous girl - and ca… |
| r11 | S01_E10 - The Golden Journey | 2331000 | B&W | 01_10 | 1962-12-06 00:00:00 | Roger Moore, Erica Rogers, Stella Bonheur | Simon undergoes considerable discomfort to bring … |


### Try-load episodes: **116** rows parsed (with filters above if any)


---

## 33. `Secret Agent _ Danger Man`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |  |
| r1 | Episode | B&W/Color | 30/60 minute ep | Season/Episode | Year/Original Airdate | Stars | Synopsis |
| r2 | Series 1_EP 01 - View From The Villa | B&W | 30 | 01_01 | 1961-04-05 00:00:00 | Patrick McGoohan, Barbara Shelley, Delphi Lawrence | The killing of a man who embezzled five million d… |
| r3 | Series 1_EP 02 - Time To Kill | B&W | 30 | 01_02 | 1960-09-18 00:00:00 | Patrick McGoohan, Sarah Lawson, Lionel Murton | When a professor's murdered in broad daylight, NA… |
| r4 | Series 1_EP 03 - Josetta | B&W | 30 | 01_03 | 1960-09-25 00:00:00 | Patrick McGoohan, Kenneth Haigh, Julia Arnall | A foreign senator is murdered in the presence of … |
| r5 | Series 1_EP 04 - The Blue Veil | B&W | 30 | 01_04 | 1960-10-02 00:00:00 | Patrick McGoohan, Laurence Naismith, Lisa Gastoni | John Drake visits the Arabian coast to investigat… |
| r6 | Series 1_EP 05 - The Lovers | B&W | 30 | 01_05 | 1960-10-09 00:00:00 | Patrick McGoohan, Maxine Audley, Martin Miller | Baravian President Pablo Gomez and his wife Maria… |
| r7 | Series 1_EP 06 - The Girl In Pink Pajamas | B&W | 30 | 01_06 | 1960-10-16 00:00:00 | Patrick McGoohan, Angela Browne, John Crawford | A young lady is found wandering the countryside, … |
| r8 | Series 1_EP 07 - Position Of Trust | B&W | 30 | 01_07 | 1960-10-23 00:00:00 | Patrick McGoohan, Donald Pleasence, Lois Maxwell | A corrupt Arabian government is selling opium dir… |
| r9 | Series 1_EP 08 - The Lonely Chair | B&W | 30 | 01_08 | 1960-10-30 00:00:00 | Patrick McGoohan, Hazel Court, Sam Wanamaker | Patrick Laurence, a wealthy, wheelchair-bound man… |
| r10 | Series 1_EP 09 - The Sanctuary | B&W | 30 | 01_09 | 1960-11-06 00:00:00 | Patrick McGoohan, Kieron Moore, Wendy Williams | Liamond, a rebel jailed several years ago for a b… |
| r11 | Series 1_EP 10 - An Affair Of State | B&W | 30 | 01_10 | 1960-11-13 00:00:00 | Patrick McGoohan, Patrick Wymark, John Le Mesurier | John Drake visits the tiny nation of San Pablo to… |


### Try-load episodes: **86** rows parsed (with filters above if any)


---

## 34. `Roy Rogers`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |
| r1 | Episode | Season/Episode | Original Airdate | Stars | Synopsis |
| r2 | 001 - Jailbreak | 01_01 | 1951-12-30 00:00:00 | Roy Rogers, Trigger, Dale Evans | A young man has been wrongly accused of murdering… |
| r3 | 002 - Doc Stevens’ Traveling Store | 01_02 | 1952-01-06 00:00:00 | Roy Rogers, Trigger, Dale Evans | Gregarious old "Doc" Stevens travels the territor… |
| r4 | 003 - The Set-Up | 01_03 | 1952-01-20 00:00:00 | Roy Rogers, Trigger, Dale Evans | An outlaw gang tries to kill crusty old Granny Ho… |
| r5 | 004 - Treasure Of Howling Dog Canyon | 01_04 | 1952-01-27 00:00:00 | Roy Rogers, Trigger, Dale Evans | A saloon girl marries a miner, then has him murde… |
| r6 | 005 - The Train Robbery | 01_05 | 1952-02-03 00:00:00 | Roy Rogers, Trigger, Dale Evans | A crooked postmaster hires two gunmen to rob a tr… |
| r7 | 006 - Badman’s Brother | 01_06 | 1952-02-10 00:00:00 | Roy Rogers, Trigger, Dale Evans | Stu Trumbull is idolized by his 11-year-old young… |
| r8 | 007 - Outlaw’s Girl | 01_07 | 1952-02-17 00:00:00 | Roy Rogers, Trigger, Dale Evans | Thelma, a young and naive friend of Dale's, has f… |
| r9 | 008 - The Desert Fugitive | 01_08 | 1952-02-24 00:00:00 | Roy Rogers, Trigger, Dale Evans | Roy helps his friend Bill Harris find the killer … |
| r10 | 009 - Outlaw’s Town | 01_09 | 1952-03-02 00:00:00 | Roy Rogers, Trigger, Dale Evans | Roy and Pat pose as outlaws and travel to a deser… |
| r11 | 010 - The Unwilling Outlaw | 01_10 | 1952-03-09 00:00:00 | Roy Rogers, Trigger, Dale Evans | Roy investigates when a law-abiding bank employee… |


### Try-load episodes: **100** rows parsed (with filters above if any)


---

## 35. `Red Skelton - Color Episode`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Episode | TRT | B&W/Color | CC | SF Numbering | Season/Episode | Original Airdate |
| r1 | S15-E01_How Stupid Of Cupid | 0:40:13 | Color |  | 1502 | 15_01 | 1965-09-14 00:00:00 |
| r2 | S15-E02_Fastest Crumb In The West | 0:40:29 | Color |  | 1503 | 15_02 | 1965-09-21 00:00:00 |
| r3 | S15-E03_Loafer Come Back To Me | 0:39:45 | Color |  | 1506 | 15_03 | 1965-09-28 00:00:00 |
| r4 | S15-E04_Who’s Afraid Of The Big Bad Wife? | 0:40:22 | Color |  | 1504 | 15_04 | 1965-10-05 00:00:00 |
| r5 | S15-E06_A Taste Of Money | 0:40:17 | Color |  | 1507 | 15_06 | 1965-10-19 00:00:00 |
| r6 | S15-E07_Here Comes The Bribe | 0:40:44 | Color |  | 1508 | 15_07 | 1965-10-26 00:00:00 |
| r7 | S15-E08_Hobo A Go Go | 0:40:46 | Color |  | 1501 | 15_08 | 1965-11-02 00:00:00 |
| r8 | S15-E09_Brats In Your Belfry | 0:40:34 | Color |  | 1509 | 15_09 | 1965-11-09 00:00:00 |
| r9 | S15-E10_Goofy Goofy Gander | 0:40:17 | Color |  | 1510 | 15_10 | 1965-11-16 00:00:00 |
| r10 | S15-E11_Somebody Down Here Hates Me | 0:39:27 | Color |  | 1511 | 15_11 | 1965-11-30 00:00:00 |
| r11 | S15-E12_Never On Bum-Day | 0:40:25 | Color |  | 1512 | 15_12 | 1965-12-07 00:00:00 |


### Try-load episodes: **139** rows parsed (with filters above if any)


---

## 36. `Renegade`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `renegade`

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `renegade`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | S01E01 - Renegade | 01_01 | 1992-09-19 00:00:00 | Lorenzo Lamas, Branscombe Richmond, Kathleen Kinmont | In the series pilot, Det. Reno Raines (Lorenzo La… |  |
| r3 | S01E02 - Hunting Accident | 01_02 | 1992-09-26 00:00:00 | Lorenzo Lamas, Branscombe Richmond, Kathleen Kinmont | Reno (Lorenzo Lamas) runs a bully (Pete Koch) out… |  |
| r4 | S01E03 - Final Judgement | 01_03 | 1992-10-03 00:00:00 | Lorenzo Lamas, Branscombe Richmond, Kathleen Kinmont | Reno races the police to capture a hired killer i… |  |
| r5 | S01E04 - La Mala Sombra | 01_04 | 1992-10-10 00:00:00 | Lorenzo Lamas, Branscombe Richmond, Kathleen Kinmont | Reno's pursuit of the alleged leader of an El Sal… |  |
| r6 | S01E05 - Mother Courage | 01_05 | 1992-10-17 00:00:00 | Lorenzo Lamas, Branscombe Richmond, Kathleen Kinmont | Reno infiltrates a group of bikers to find a mech… |  |
| r7 | S01E06 - Second Chance | 01_06 | 1992-10-24 00:00:00 | Lorenzo Lamas, Branscombe Richmond, Kathleen Kinmont | Reno chases a racketeer (James Darren) who attrac… |  |
| r8 | S01E07 - Eye Of The Storm | 01_07 | 1992-10-31 00:00:00 | Lorenzo Lamas, Branscombe Richmond, Kathleen Kinmont | A ruthless band of murderers escape jail and trac… |  |
| r9 | S01E08 - Payback | 01_08 | 1992-11-07 00:00:00 | Lorenzo Lamas, Branscombe Richmond, Kathleen Kinmont | A bust goes horribly wrong and results in an info… |  |
| r10 | S01E09 - The Talisman | 01_09 | 1992-11-14 00:00:00 | Lorenzo Lamas, Branscombe Richmond, Kathleen Kinmont | Reno teams up with a rather rambunctious teenage … |  |
| r11 | S01E10 - Partners | 01_10 | 1992-11-21 00:00:00 | Lorenzo Lamas, Branscombe Richmond, Ed Lauter | When Reno's mentor on the police force is killed … |  |


### Try-load episodes: **110** rows parsed (with filters above if any)


---

## 37. `Republic Of Doyle - NOTE - Epis`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** yes — read tab instructions

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | NOTE - Episodes in red are not in house |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | S01E01 - Fathers And Sons | 01_01 | 2010-01-06 00:00:00 | Allan Hawco, Sean McGinley, Lynda Boyd | The Doyles help a close family friend beat a mans… |  |
| r3 | S01E02 - The Return Of The Grievous Angel | 01_02 | 2010-01-13 00:00:00 | Allan Hawco, Sean McGinley, Lynda Boyd | The Doyles are hired by a young woman looking to … |  |
| r4 | S01E03 - Duchess Of George | 01_03 | 2010-01-20 00:00:00 | Allan Hawco, Sean McGinley, Lynda Boyd | The Doyles are hired to find out if the burning o… |  |
| r5 | S01E04 - Blood Is Thicker Than Blood | 01_04 | 2010-01-27 00:00:00 | Allan Hawco, Peter MacNeill, Krystin Pellerin | An ex-con wrongfully convicted of his wife's murd… |  |
| r6 | S01E05 - Hit And Rum | 01_05 | 2010-02-03 00:00:00 | Allan Hawco, Sean McGinley, Lynda Boyd | An investigation to see if their client's husband… |  |
| r7 | S01E06 - The One Who Got Away | 01_06 | 2010-02-10 00:00:00 | Allan Hawco, Sean McGinley, Lynda Boyd | The Doyles show their sentimental side as they he… |  |
| r8 | S01E07 - The Woman Who Knew Too Little | 01_07 | 2010-03-03 00:00:00 | Allan Hawco, Sean McGinley, Lynda Boyd | Jake sets out to find the true identity of a beau… |  |
| r9 | S01E08 - The Tell-Tale Safe | 01_08 | 2010-03-10 00:00:00 | Allan Hawco, Sean McGinley, Lynda Boyd | A grieving widow hires the Doyles to find out why… |  |
| r10 | S01E09 - He Sleeps With The Chips | 01_09 | 2010-03-17 00:00:00 | Allan Hawco, Sean McGinley, Lynda Boyd | When a dubious chip truck owner notices his truck… |  |
| r11 | S01E10 - The Pen Is Mightier Than The Doyle | 01_10 | 2010-03-24 00:00:00 | Allan Hawco, Sean McGinley, Lynda Boyd | Jake is dogged by mystery writer Garrison Steele … |  |


### Try-load episodes: **77** rows parsed (with filters above if any)


---

## 38. `Route 66`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | S1_E01 - Black November | 01_01 | 1960-10-07 00:00:00 | Martin Milner, George Maharis, Everett Sloane | Leaving New York City behind, Tod and Buz begin t… |  |
| r3 | S1_E02 - A Lance Of Straw | 01_02 | 1960-10-14 00:00:00 | Janice Rule, Martin Milner, George Maharis | Tod and Buz reach the destination they started fo… |  |
| r4 | S1_E03 - The Swan Bed | 01_03 | 1960-10-21 00:00:00 | Betty Field, Martin Milner, George Maharis | Tod and Buz layover to work in New Orleans and ma… |  |
| r5 | S1_E04 - The Man On The Monkey Board | 01_04 | 1960-10-28 00:00:00 | Lew Ayres, Martin Milner, George Maharis | Tod and Buz take labor jobs on a Louisiana offsho… |  |
| r6 | S1_E05 - The Strengthening Angels | 01_05 | 1960-11-04 00:00:00 | Suzanne Pleshette, Martin Milner, George Maharis | Tod and Buz, driving through California "West by … |  |
| r7 | S1_E06 - Ten Drops Of Water | 01_06 | 1960-11-11 00:00:00 | Martin Milner, George Maharis, Brut Brinckerhoff | Tod and Buz,working as ranch hands in a drought s… |  |
| r8 | S1_E07 - Three Sides | 01_07 | 1960-11-18 00:00:00 | Martin Milner, George Maharis, E.G. Marshall | Tod and Buz inadvertently become involved in the … |  |
| r9 | S1_E08 - Legacy For Lucia | 01_08 | 1960-11-25 00:00:00 | Martin Milner, George Maharis, Jay C. Flippen | Tod and Buz, now working in a small town Oregon s… |  |
| r10 | S1_E09 - Layout At Glen Canyon | 01_09 | 1960-12-02 00:00:00 | Martin Milner, George Maharis, Charles McGraw | Tod and Buz, working as laborers near Page, Arizo… |  |
| r11 | S1_E10 - The Beryllium Eater | 01_10 | 1960-12-09 00:00:00 | Martin Milner, George Maharis, Inger Stevens | Tod and Buz, working as laborers at a large scale… |  |


### Try-load episodes: **116** rows parsed (with filters above if any)


---

## 39. `The Prisoner`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | The Prisoner |  |  |  |  |  |  |
| r1 | Episode | TRT | Color/B&W | CC | Season/Episode | Year/Original Airdate | Stars |
| r2 | EP 01 - Arrival | 0:45:00 | Color |  | 01_00 | 1968-06-01 00:00:00 | Patrick McGoohan, Virginia Maskell, Guy Doleman |
| r3 | EP 02 - The Chimes Of Big Ben | 0:45:00 | Color |  | 01_01 | 1967-10-08 00:00:00 | Patrick McGoohan, Leo McKern, Nadia Gray |
| r4 | EP 03 - A, B And C | 0:44:59 | Color |  | 01_02 | 1967-10-15 00:00:00 | Patrick McGoohan, Katherine Kath, Sheila Allen |
| r5 | EP 04 - Free For All | 0:45:00 | Color |  | 01_03 | 1967-10-22 00:00:00 | Patrick McGoohan, Eric Portman, Rachel Herbert |
| r6 | EP 05 - The Schizoid Man | 0:45:00 | Color |  | 01_04 | 1967-10-29 00:00:00 | Patrick McGoohan, Jane Merrow, Anton Rodgers |
| r7 | EP 06 - The General | 0:45:00 | Color |  | 01_05 | 1967-11-05 00:00:00 | Patrick McGoohan, Colin Gordon, John Castle |
| r8 | EP 07 - Many Happy Returns | 0:44:57 | Color |  | 01_06 | 1967-11-12 00:00:00 | Patrick McGoohan, Donald Sinden, Patrick Cargill |
| r9 | EP 08 - Dance Of The Dead | 0:45:00 | Color |  | 01_07 | 1967-11-26 00:00:00 | Patrick McGoohan, Mary Morris, Duncan Macrae |
| r10 | EP 09 - Checkmate | 0:44:59 | Color |  | 01_08 | 1968-08-17 00:00:00 | Patrick McGoohan, Ronald Radd, Patricia Jessel |
| r11 | EP 10 - Hammer Into Anvil | 0:45:00 | Color |  | 01_09 | 1967-12-10 00:00:00 | Patrick McGoohan, Patrick Cargill, Victor Maddern |


### Try-load episodes: **17** rows parsed (with filters above if any)


---

## 40. `silk stalkings`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r1 | Episode | TRT | Color/B&W | CC | Season/Episode | Year/Original Airdate | Stars |
| r2 | SLK_101 - Pilot | 0:45:16 | Color | scc | 01_01 | 1991-11-07 00:00:00 | Mitzi Kapture, Rob Estes, Ann Turkel |
| r3 | SLK_102 - Going To Babylon | 0:45:44 | Color | scc | 01_02 | 1991-11-14 00:00:00 | Mitzi Kapture, Rob Estes, R.G. Armstrong |
| r4 | SLK_103 - S.O.B. | 0:45:24 | Color | scc | 01_03 | 1991-11-21 00:00:00 | Mitzi Kapture, Rob Estes, Shari Shattuck |
| r5 | SLK_104 - In The Name Of Love | 0:45:13 | Color | scc | 01_04 | 1991-11-28 00:00:00 | Mitzi Kapture, Rob Estes, Pamela Bowen |
| r6 | SLK_105 - Men Seeking Women | 0:45:12 | Color | scc | 01_05 | 1991-12-05 00:00:00 | Mitzi Kapture, Rob Estes, Ilan Mitchell-Smith |
| r7 | SLK_106 - Dirty Laundry | 0:43:56 | Color | scc | 01_06 | 1991-12-12 00:00:00 | Mitzi Kapture, Rob Estes, Martha Byrne |
| r8 | SLK_107 - Hardcopy | 0:45:15 | Color | scc | 01_07 | 1991-12-19 00:00:00 | Mitzi Kapture, Rob Estes, Terri Treas |
| r9 | SLK_108 - Curtain Call | 0:44:32 | Color | scc | 01_08 | 1992-01-02 00:00:00 | Mitzi Kapture, Rob Estes, Kelly Curtis |
| r10 | SLK_109 - The Brotherhood | 0:45:02 | Color | scc | 01_09 | 1992-01-09 00:00:00 | Mitzi Kapture, Rob Estes, William McNamara |
| r11 | SLK_110 - Blo-Dri | 0:44:56 | Color | scc | 01_10 | 1992-01-16 00:00:00 | Mitzi Kapture, Rob Estes, Teri Ann Linn |


### Try-load episodes: **176** rows parsed (with filters above if any)


---

## 41. `Space_ 1999`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | S1E01 - Breakaway | 01_01 | 1975-09-21 00:00:00 | Martin Landau, Barbara Bain, Barry Morse | Commander John Koenig, the new commander of Moonb… |  |
| r3 | S1E02 - Force Of Life | 01_02 | 1975-09-11 00:00:00 | Martin Landau, Barbara Bain, Barry Morse | A wandering energy force inhabits the body of Alp… |  |
| r4 | S1E03 - Collision Course | 01_03 | 1975-09-18 00:00:00 | Martin Landau, Barbara Bain, Barry Morse | After destroying an asteroid on a collision cours… |  |
| r5 | S1E04 - War Games | 01_04 | 1975-09-25 00:00:00 | Martin Landau, Barbara Bain, Barry Morse | Moonbase Alpha is attacked and devastated by wars… |  |
| r6 | S1E05 - Death’s Other Dominion | 01_05 | 1975-10-02 00:00:00 | Martin Landau, Barbara Bain, Barry Morse | On the ice world of Ultima Thule the Alphans enco… |  |
| r7 | S1E06 - Voyager’s Return | 01_06 | 1975-10-09 00:00:00 | Martin Landau, Barbara Bain, Barry Morse | The Alphans encounter the Voyager space probe tha… |  |
| r8 | S1E07 - Alpha Child | 01_07 | 1975-10-16 00:00:00 | Martin Landau, Barbara Bain, Barry Morse | The Alphans' joy turns to horror when the first c… |  |
| r9 | S1E08 - Dragon’s Domain | 01_08 | 1975-10-23 00:00:00 | Martin Landau, Barbara Bain, Barry Morse | Discredited eagle pilot Tony Cellini is beset by … |  |
| r10 | S1E09 - Mission Of The Darians | 01_09 | 1975-10-30 00:00:00 | Martin Landau, Barbara Bain, Barry Morse | The Alphans encounter a miles-long ark from the p… |  |
| r11 | S1E10 - Black Sun | 01_10 | 1975-11-06 00:00:00 | Martin Landau, Barbara Bain, Barry Morse | The moon is approaching a black hole. Professor B… |  |


### Try-load episodes: **48** rows parsed (with filters above if any)


---

## 42. `The Texan - Note - missing epis`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `texan`

- **Name contains NOTE/Note:** yes — read tab instructions

- **Parser style (default → effective):** `texan`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Note - missing episodes are highlighted in red |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | S1_EP01 - Law Of The Gun |  | 1958-09-29 00:00:00 | Rory Calhoun, Neville Brand, John Larch | Bill Longley arrives in a small Texas town with t… |  |
| r3 | S1_EP02 - Man With The Gold Star | 01_02 | 1958-10-06 00:00:00 | Rory Calhoun, Thomas Gomez, Bruce Bennett | Professional gambler Jake Romer wins big in a pok… |  |
| r4 | S1_EP03 - The Troubled Town | 01_03 | 1958-10-13 00:00:00 | Rory Calhoun, Pat Conway, James Drury | Hot-headed Johnny Kaler, embarrassed that he's be… |  |
| r5 | S1_EP04 - First Notch | 01_04 | 1958-10-20 00:00:00 | Rory Calhoun, J. Carrol Naish, Peggie Castle | Bill Longley meets an old, but beautiful, friend … |  |
| r6 | S1_EP05 - The Edge Of The Cliff | 01_05 | 1958-10-27 00:00:00 | Rory Calhoun, Sidney Blackmer, Barbara Baxley | Orin and Ruth McKnight's May/December romance hit… |  |
| r7 | S1_EP06 - Jail For Innocents | 01_06 | 1958-11-03 00:00:00 | Rory Calhoun, Ray Ferrell, Vaughn Taylor | While sleeping by his campsite, Bill is startled … |  |
| r8 | S1_EP07 - A Tree For Planting | 01_07 | 1958-11-10 00:00:00 | Rory Calhoun, James Westerfield, Lurene Tuttle | Bill Longley comes to the aid of Ramirez, a farme… |  |
| r9 | S1_EP08 - Hemp Tree | 01_08 | 1958-11-17 00:00:00 | Rory Calhoun, Michael Landon, Stuart Randall | The $8300 Bill Longley earned for driving a herd … |  |
| r10 | S1_EP09 - Widow Of Paradise | 01_09 | 1958-11-24 00:00:00 | Rory Calhoun, Charles Watts, Russell Thorson | After Longley is forced to kill a barfly that tri… |  |
| r11 | S1_EP10 - Desert Passage | 01_10 | 1958-12-01 00:00:00 | Rory Calhoun, R. G. Armstrong, George Barrows |  |  |


### Try-load episodes: **78** rows parsed (with filters above if any)


---

## 43. `The Lone Ranger`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r1 | Episode | TRT | Season/Episode |
| r2 | 001 - Enter The Lone Ranger | 0:22:39 | 01_01 |
| r3 | 002 - The Lone Ranger Fights On | 0:22:43 | 01_02 |
| r4 | 003 - The Lone Ranger’s Triumph | 0:22:43 | 01_03 |
| r5 | 004 - Legion Of Old Timers | 0:23:03 | 01_04 |
| r6 | 005 - Rustlers’ Hideout | 0:22:54 | 01_05 |
| r7 | 006 - War Horse | 0:24:40 | 01_06 |
| r8 | 007 - Pete And Pedro | 0:24:53 | 01_07 |
| r9 | 008 - The Renegades | 0:25:11 | 01_08 |
| r10 | 009 - The Tenderfeet | 0:22:37 | 01_09 |
| r11 | 010 - High Heels | 0:22:58 | 01_10 |


### Try-load episodes: **221** rows parsed (with filters above if any)


---

## 44. `ALF 2025`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r1 | Episode | TRT | Color/B&W | CC | Season/Episode | Year/Original Airdate | Stars |
| r2 | 101 - Pilot | 2024-05-23 20:35:00 | Color | scc |  | 2022-04-01 00:00:00 | Max Wright, Anne Schedeen, Andrea Elson |
| r3 | 102 - Strangers In The Night | 2024-05-23 21:28:00 | Color | scc | 01_02 | 1986-09-29 00:00:00 | Max Wright, Anne Schedeen, Andrea Elson |
| r4 | 103 - Looking For Lucky | 2024-05-23 21:20:00 | Color | scc | 01_03 | 10/6/86 | Max Wright, Anne Schedeen, Andrea Elson |
| r5 | 104 - Pennsylvania 6-5000 | 2024-05-23 20:58:00 | Color | scc | 01_04 | 1986-10-13 00:00:00 | Max Wright, Anne Schedeen, Andrea Elson |
| r6 | 105 - Keepin’ The Faith | 2024-05-23 21:27:00 | Color | scc | 01_05 | 1986-10-20 00:00:00 | Max Wright, Anne Schedeen, Andrea Elson |
| r7 | 106 - For Your Eyes Only | 2024-05-23 20:14:00 | Color | scc | 01_06 | 1986-11-03 00:00:00 | Max Wright, Anne Schedeen, Andrea Elson |
| r8 | 107 - Help Me, Rhonda | 2024-05-23 20:53:00 | Color | scc | 01_07 | 1986-11-10 00:00:00 | Max Wright, Anne Schedeen, Andrea Elson |
| r9 | 108 - Don’t It Make Your Brown Eyes Blue | 2024-05-23 20:35:00 | Color | scc | 01_08 | 1986-11-17 00:00:00 | Max Wright, Anne Schedeen, Andrea Elson |
| r10 | 109 - Jump | 2024-05-23 21:28:00 | Color | scc | 01_09 | 1986-11-24 00:00:00 | Max Wright, Anne Schedeen, Andrea Elson |
| r11 | 110 - Baby, You Can Drive My Car | 2024-05-23 21:28:00 | Color | scc | 01_10 | 1986-12-01 00:00:00 | Max Wright, Anne Schedeen, Andrea Elson |


### Try-load episodes: **97** rows parsed (with filters above if any)


---

## 45. `Tim Conway Comedy Hour - Note -`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `tim_conway`

- **Name contains NOTE/Note:** yes — read tab instructions

- **Parser style (default → effective):** `leading_episode` + YAML override `leading_episode`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Note - CC files included in folder |  |  |  |  |  |
| r1 | Episode | Season/Episode | Original Airdate | Stars | Synopsis | Notes |
| r2 | 101 - Guests: Dan Rowan & Lana Turner | 01_01 | 1970-09-20 00:00:00 | Tim Conway, Dan Rowan, Lana Turner | Highlights include: Lana and Dan hiring a bumblin… |  |
| r3 | 102 - Guests: Barbara Feldon & David Jansen | 01_02 | 1970-09-27 00:00:00 | Tim Conway, Barbara Feldon, David Janssen | Tonight's episode features: Janssen as a pirate w… |  |
| r4 | 103 - Guests: Dick Martin & Joan Crawford | 01_03 | 1970-10-04 00:00:00 | Tim Conway, Dick Martin, Joan Crawford | All aboard for laughter when Tim and his guests t… |  |
| r5 | 104 - Guests: Audrey Meadows & Peter Graves | 01_04 | 1970-10-11 00:00:00 | Tim Conway, Audrey Meadows, Peter Graves | Tim and Peter play competing holdup men robbing a… |  |
| r6 | 105 - Guests: Jane Powell And Carl Reiner | 01_05 | 1970-10-18 00:00:00 | Tim Conway, Jane Powell, Carl Reiner | Tim and his guests spoof "Phantom Of The Opera"; … |  |
| r7 | 106 - Guests: Tony Randall & Janet Leigh | 01_06 | 1970-10-25 00:00:00 | Tim Conway, Tony Randall, Janet Leigh | Leigh plays a sultry German chanteuse who serenad… |  |
| r8 | 107 - Guests: Dan Blocker, Imogena Coca, Sergio M… | 01_07 | 1970-11-01 00:00:00 | Tim Conway, Imogene Coca, Dan Blocker | Guests Blocker and Coca join Tim for an on-pointe… |  |
| r9 | 108 - Shelley Winters, John Forsythe, Jackie DeSh… | 01_08 | 1970-11-08 00:00:00 | Tim Conway, Shelley Winters, John Forsythe | Shelly tries to hide Tooth Fairy Tim from her jea… |  |
| r10 | 109 - Carol Burnett And Steve Lawrence | 01_09 | 1970-11-15 00:00:00 | Tim Conway, Steve Lawrence, Carol Burnett | Carol and Steve join Tim for a sketch about three… |  |
| r11 | 110 - Guests: Merv Griffin, Judy Carne | 01_10 | 1970-11-22 00:00:00 | Tim Conway, Merv Griffin, Judy Carne | Highlights include Merv and Judy as conniving rel… |  |


### Try-load episodes: **14** rows parsed (with filters above if any)


---

## 46. `Tim Conway Show`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | Table 1 |  |  |  |  |  |
| r1 | Episode | Season/Episode | Original Airdate | Stars | Synopsis | Notes |
| r2 | 101 - Burt Reynolds, Michele Lee | 01_01 | 1980-03-22 00:00:00 | Tim Conway, Michele Lee | Tim invites audience members onstage to perform i… |  |
| r3 | 102 - K.C. & The Sunshine Band | 01_02 | 1980-03-29 00:00:00 | Tim Conway, Carol Burnett | Carol Burnett dons her Mrs. Wiggins attire and dr… |  |
| r4 | 103 - Melba Moore | 01_03 | 1980-04-05 00:00:00 | Tim Conway, Bert Berdis, Eric Boardman | Don Knotts gets blackmailed by Tim to get him to … |  |
| r5 | 104 - Susan Anton & Suazanne Sommers | 01_04 | 1980-04-12 00:00:00 | Tim Conway, Suan Anton, Bert Berdis | Jack Reiley wears a Suzanne Sommers mask to prete… |  |
| r6 | 105 - Barbara Mandrell & Dick Martin | 01_05 | 1980-04-19 00:00:00 | Tim Conway, Bert Berdis, The Don Crichton Dancers | Dick Martin interrupts the start of the show to d… | SEASON ONE IS ALL ONE HOURS |
| r7 | 106 - Bernadette Peters | 01_06 | 1980-04-26 00:00:00 | Tim Conway, Bert Berdis, The Don Crichton Dancers | Bernadette catches Tim pretending to make love to… |  |
| r8 | 107 - Helen Reddy & David Copperfield | 01_07 | 1980-05-03 00:00:00 | Tim Conway, Bert Berdis, Don Crichton | David Copperfield tears up Tim's cue-card then ma… |  |
| r9 | 108 - The Village People | 01_08 | 1980-05-10 00:00:00 | Tim Conway, Bert Berdis, Alex Briley | Tim's introductory script is missing pages so he … |  |
| r10 | 109 - Mel Tillis | 01_09 | 1980-05-17 00:00:00 | Tim Conway, Bert Berdis, The Don Crichton Dancers | Stuttering Mel Tillis always gives a perfect perf… |  |
| r11 | 201 - Spoof Of TV Show "Dallas" | 02_01 | 1980-09-20 00:00:00 | Tim Conway, Bert Berdis, The Don Crichton Dancers | Tim strikes comedic oil in a rich spoof of the hi… |  |


### Try-load episodes: **31** rows parsed (with filters above if any)


---

## 47. `Wiseguy - NOTE - Episode titles`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** no (add `shows:` entry if this is a series)

- **Name contains NOTE/Note:** yes — read tab instructions

- **Parser style (default → effective):** `generic`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | NOTE - Episode titles in red are missing |  |  |  |  |  |
| r1 | Episode | Season/Episode | Year/Original Airdate | Stars | Synopsis | Notes |
| r2 | S01E01 - Pilot | 01_01 | 1987-09-16 00:00:00 | Ken Wahl, Jonathan Banks, Jim Byrnes | This was the pilot for the hit series. Ken Wahl s… |  |
| r3 | S01E02 - New Blood | 01_02 | 1987-09-24 00:00:00 | Ken Wahl, Jonathan Banks, Jim Byrnes | In an attempt to take over Sonny Steelgrave's bus… |  |
| r4 | S01E03 - The Loose Cannon | 01_03 | 1987-10-01 00:00:00 | Ken Wahl, Jonathan Banks, Jim Byrnes | A psychopathic murderer posing as Sonny's nephew … |  |
| r5 | S01E04 - The Birthday Surprise | 01_04 | 1987-10-08 00:00:00 | Ken Wahl, Jonathan Banks, Jim Byrnes | When Vinnie's young cousin, a boxer, is found dea… |  |
| r6 | S01E05 - One On One | 01_05 | 1987-10-15 00:00:00 | Ken Wahl, Jonathan Banks, Jim Byrnes | When the local cops put the heat on Sonny Steelgr… |  |
| r7 | S01E06 - The Prodigal Son | 01_06 | 1987-10-22 00:00:00 | Ken Wahl, Jonathan Banks, Jim Byrnes | After his mother is mugged in Brooklyn, an enrage… |  |
| r8 | S01E07 - A Deal’s A Deal | 01_07 | 1987-10-29 00:00:00 | Ken Wahl, Jonathan Banks, Jim Byrnes | Sonny's cruel punishment of a lounge singer who w… |  |
| r9 | S01E08 - The Marriage Of Heaven And Hell | 01_08 | 1987-11-05 00:00:00 | Ken Wahl, Jonathan Banks, Jim Byrnes | Sonny's impending marriage to a syndicate boss' d… |  |
| r10 | S01E09 - No One Get Out Of Here Alive | 01_09 | 1987-11-12 00:00:00 | Ken Wahl, Jonathan Banks, Jim Byrnes | An outraged Sonny Steelgrave accuses Vinnie of be… |  |
| r11 | S01E10 - Last Rites For Lucci | 01_10 | 1987-11-19 00:00:00 | Ken Wahl, Jonathan Banks, Jim Byrnes | In the aftermath of the Steelgrave case, Vinnie t… |  |


### Try-load episodes: **74** rows parsed (with filters above if any)


---

## 48. `2025 JIM BOWIE`

- **Checklist:** [ ] Reviewed parser + columns + special rules

- **In april_2026.yaml:** yes → `jim_bowie`

- **Name contains NOTE/Note:** no

- **Parser style (default → effective):** `jim_bowie`

### Top-of-sheet preview (first non-empty rows, truncated)

| r0 | : S1 E1 - The Birth Of The Blade |
| r1 | : S1 E2 - The Squatter |
| r2 | : S1 E3 - The Adventure With Audubon |
| r3 | : S1 E4 - Deputy Sheriff |
| r4 | : S1 E5 - Trapline |
| r5 | : S1 E6 - Broomstick Wedding |
| r6 | : S1 E7 - Natchez Trace |
| r7 | S1 E8 - Jim Bowie Comes Home |
| r8 | S1 E9 - The Ghost Of Jean Battoo |
| r9 | : S1 E10 - The Secessionist |
| r10 | S1 E11 - Land Jumpers |
| r11 | S1 E12 - The Select Females |


### Try-load episodes: **76** rows parsed (with filters above if any)


---
