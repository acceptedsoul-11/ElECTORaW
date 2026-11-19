from __future__ import annotations

import re
from typing import Any


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


# The 2024 Lok Sabha winners below are joined to the Union Cabinet list
# published by the Prime Minister's Office. Rajya Sabha-only ministers are
# intentionally not included because this feature is a Lok Sabha winner view.
NDA_CABINET_MINISTERS: list[dict[str, Any]] = [
    {"name": "Narendra Modi", "aliases": ["NARENDRA MODI"], "party": "BJP", "portfolio": "Prime Minister", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Rajnath Singh", "aliases": ["RAJ NATH SINGH", "RAJNATH SINGH"], "party": "BJP", "portfolio": "Defence", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Amit Shah", "aliases": ["AMIT SHAH"], "party": "BJP", "portfolio": "Home Affairs; Cooperation", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Nitin Gadkari", "aliases": ["NITIN JAIRAM GADKARI"], "party": "BJP", "portfolio": "Road Transport and Highways", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Shivraj Singh Chouhan", "aliases": ["SHIVRAJ SINGH CHOUHAN"], "party": "BJP", "portfolio": "Agriculture and Farmers Welfare; Rural Development", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Manohar Lal", "aliases": ["MANOHAR LAL"], "party": "BJP", "portfolio": "Housing and Urban Affairs; Power", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Piyush Goyal", "aliases": ["PIYUSH GOYAL"], "party": "BJP", "portfolio": "Commerce and Industry", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Dharmendra Pradhan", "aliases": ["DHARMENDRA PRADHAN"], "party": "BJP", "portfolio": "Education", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Sarbananda Sonowal", "aliases": ["SARBANANDA SONOWAL"], "party": "BJP", "portfolio": "Ports, Shipping and Waterways", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Virendra Kumar", "aliases": ["DR VIRENDRA KUMAR", "VIRENDRA KUMAR"], "party": "BJP", "portfolio": "Social Justice and Empowerment", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Prahlad Joshi", "aliases": ["PRALHAD JOSHI", "PRAHLAD JOSHI"], "party": "BJP", "portfolio": "Consumer Affairs, Food and Public Distribution", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Gajendra Singh Shekhawat", "aliases": ["GAJENDRA SINGH SHEKHAWAT"], "party": "BJP", "portfolio": "Culture and Tourism", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Kiren Rijiju", "aliases": ["KIREN RIJIJU"], "party": "BJP", "portfolio": "Parliamentary Affairs; Minority Affairs", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Mansukh Mandaviya", "aliases": ["DR MANSUKH MANDAVIYA", "MANSUKH MANDAVIYA"], "party": "BJP", "portfolio": "Labour and Employment; Youth Affairs and Sports", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Jyotiraditya Scindia", "aliases": ["JYOTIRADITYA M SCINDIA", "JYOTIRADITYA M. SCINDIA"], "party": "BJP", "portfolio": "Communications; Development of North Eastern Region", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Jual Oram", "aliases": ["JUAL ORAM"], "party": "BJP", "portfolio": "Tribal Affairs", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80"},
    {"name": "Rajiv Ranjan Singh", "aliases": ["RAJIV RANJAN SINGH ALIAS LALAN SINGH"], "party": "JD(U)", "portfolio": "Panchayati Raj; Fisheries, Animal Husbandry and Dairying", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Janata_Dal_(United)_flag.svg?width=80"},
    {"name": "Jitan Ram Manjhi", "aliases": ["JITAN RAM MANJHI"], "party": "HAMS", "portfolio": "Micro, Small and Medium Enterprises", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Hindustani_Awam_Morcha_flag.svg?width=80"},
    {"name": "Kinjarapu Ram Mohan Naidu", "aliases": ["KINJARAPU RAMMOHAN NAIDU"], "party": "TDP", "portfolio": "Civil Aviation", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Telugu_Desam_Party_flag.svg?width=80"},
    {"name": "H. D. Kumaraswamy", "aliases": ["H D KUMARASWAMY", "H.D. KUMARASWAMY"], "party": "JD(S)", "portfolio": "Heavy Industries; Steel", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/JD(S)_flag.svg?width=80"},
    {"name": "Chirag Paswan", "aliases": ["CHIRAG PASWAN"], "party": "LJPRV", "portfolio": "Food Processing Industries", "logo": "https://commons.wikimedia.org/wiki/Special:FilePath/Lok_Janshakti_Party_flag.svg?width=80"},
]


_LOGOS = {
    "BJP": "https://commons.wikimedia.org/wiki/Special:FilePath/Bharatiya%20Janata%20Party%20flag.svg?width=80",
    "LJP": "https://commons.wikimedia.org/wiki/Special:FilePath/Lok%20Janshakti%20Party_flag.svg?width=80",
    "SAD": "https://commons.wikimedia.org/wiki/Special:FilePath/Shiromani%20Akali%20Dal_flag.svg?width=80",
    "SHS": "https://commons.wikimedia.org/wiki/Special:FilePath/Shiv%20Sena_flag.svg?width=80",
}


def _historical(name: str, aliases: list[str], party: str, portfolio: str) -> dict[str, Any]:
    return {"name": name, "aliases": aliases, "party": party, "portfolio": portfolio, "logo": _LOGOS.get(party, _LOGOS["BJP"])}


# These are the Lok Sabha-winning cabinet members for each election-year
# government, joined to the ECI successful-candidate records. Rajya Sabha-only
# ministers are intentionally absent from this Lok Sabha spotlight.
CABINET_BY_YEAR: dict[int, list[dict[str, Any]]] = {
    2014: [
        _historical("Narendra Modi", ["NARENDRA MODI"], "BJP", "Prime Minister"),
        _historical("Rajnath Singh", ["RAJ NATH SINGH", "RAJNATH SINGH"], "BJP", "Home Affairs"),
        _historical("Sushma Swaraj", ["SUSHMA SWARAJ"], "BJP", "External Affairs; Overseas Indian Affairs"),
        _historical("Nitin Gadkari", ["NITIN JAIRAM GADKARI", "GADKARI NITIN JAIRAM"], "BJP", "Road Transport and Highways; Shipping"),
        _historical("Uma Bharti", ["UMA BHARTI"], "BJP", "Water Resources, River Development and Ganga Rejuvenation"),
        _historical("D. V. Sadananda Gowda", ["D V SADANANDA GOWDA", "SADANANDA GOWDA"], "BJP", "Railways"),
        _historical("Ram Vilas Paswan", ["RAM VILAS PASWAN", "RAMVILAS PASWAN"], "LJP", "Consumer Affairs, Food and Public Distribution"),
        _historical("Kalraj Mishra", ["KALRAJ MISHRA"], "BJP", "Micro, Small and Medium Enterprises"),
        _historical("Maneka Gandhi", ["MANEKA GANDHI"], "BJP", "Women and Child Development"),
        _historical("Ananth Kumar", ["ANANTH KUMAR"], "BJP", "Chemicals and Fertilizers"),
        _historical("Ravi Shankar Prasad", ["RAVI SHANKAR PRASAD"], "BJP", "Law and Justice; Communications and Information Technology"),
        _historical("Harsimrat Kaur Badal", ["HARSIMRAT KAUR BADAL"], "SAD", "Food Processing Industries"),
        _historical("Narendra Singh Tomar", ["NARENDRA SINGH TOMAR"], "BJP", "Mines, Steel and Labour and Employment"),
        _historical("Jual Oram", ["JUAL ORAM"], "BJP", "Tribal Affairs"),
        _historical("Radha Mohan Singh", ["RADHA MOHAN SINGH"], "BJP", "Agriculture and Farmers Welfare"),
        _historical("Harsh Vardhan", ["HARSH VARDHAN"], "BJP", "Health and Family Welfare; Science and Technology"),
    ],
    2019: [
        _historical("Narendra Modi", ["NARENDRA MODI"], "BJP", "Prime Minister"),
        _historical("Rajnath Singh", ["RAJ NATH SINGH", "RAJNATH SINGH"], "BJP", "Defence"),
        _historical("Amit Shah", ["AMIT SHAH"], "BJP", "Home Affairs"),
        _historical("Nitin Gadkari", ["NITIN JAIRAM GADKARI"], "BJP", "Road Transport and Highways; Micro, Small and Medium Enterprises"),
        _historical("D. V. Sadananda Gowda", ["D V SADANANDA GOWDA", "SADANANDA GOWDA"], "BJP", "Chemicals and Fertilizers"),
        _historical("Narendra Singh Tomar", ["NARENDRA SINGH TOMAR"], "BJP", "Agriculture and Farmers Welfare; Rural Development; Panchayati Raj"),
        _historical("Ravi Shankar Prasad", ["RAVI SHANKAR PRASAD"], "BJP", "Law and Justice; Communications; Electronics and Information Technology"),
        _historical("Harsimrat Kaur Badal", ["HARSIMRAT KAUR BADAL"], "SAD", "Food Processing Industries"),
        _historical("Ramesh Pokhriyal Nishank", ["RAMESH POKHRIYAL NISHANK", "RAMESH POKHRIYAL"], "BJP", "Human Resource Development"),
        _historical("Arjun Munda", ["ARJUN MUNDA"], "BJP", "Tribal Affairs"),
        _historical("Smriti Irani", ["SMRITI ZUBIN IRANI", "SMRITI IRANI"], "BJP", "Women and Child Development; Textiles"),
        _historical("Harsh Vardhan", ["HARSH VARDHAN"], "BJP", "Health and Family Welfare; Science and Technology; Earth Sciences"),
        _historical("Pralhad Joshi", ["PRALHAD JOSHI", "PRAHLAD JOSHI"], "BJP", "Parliamentary Affairs; Coal and Mines"),
        _historical("Gajendra Singh Shekhawat", ["GAJENDRA SINGH SHEKHAWAT"], "BJP", "Jal Shakti"),
        _historical("Giriraj Singh", ["GIRIRAJ SINGH"], "BJP", "Animal Husbandry, Dairying and Fisheries"),
        _historical("Mahendra Nath Pandey", ["MAHENDRA NATH PANDEY"], "BJP", "Skill Development and Entrepreneurship"),
        _historical("Arvind Ganpat Sawant", ["ARVIND GANPAT SAWANT"], "SHS", "Heavy Industries and Public Enterprises"),
    ],
    2024: NDA_CABINET_MINISTERS,
}


def matches(candidate_name: str, minister: dict[str, Any]) -> bool:
    candidate = _norm(candidate_name)
    return any(_norm(alias) in candidate or candidate in _norm(alias) for alias in [minister["name"], *minister["aliases"]])
