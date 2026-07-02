import os
import json
import requests
import anthropic
from datetime import date, timedelta
from collections import defaultdict
import calendar as cal_module
from flask import Flask, render_template, request
from dotenv import load_dotenv

try:
    from icalendar import Calendar
except ImportError:
    Calendar = None

load_dotenv()

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

PRICING_PROMPT = """You are a vacation rental pricing expert specializing in the Mexican market.

Property data provided:
- Location: {location}
- Property type: {property_type}
- Base rate: {base_rate} {currency}/night
- Current occupancy: {occupancy}
- Current pricing approach: {pricing_approach}
- Occupancy data source: {occupancy_source}

Provide pricing recommendations as valid JSON only (no markdown, no extra text):
{{
  "periods": [
    {{"name": "Low Season", "months": ["Sep", "Oct"], "multiplier": 0.85, "rate": 0}},
    {{"name": "Regular", "months": ["Nov", "Apr", "May", "Jun"], "multiplier": 1.0, "rate": 0}},
    {{"name": "High Season", "months": ["Dec", "Jan", "Feb", "Mar"], "multiplier": 1.4, "rate": 0}},
    {{"name": "Peak", "months": ["Jul", "Aug"], "multiplier": 1.6, "rate": 0}}
  ],
  "explanations": {{
    "Low Season": "Reason for these months...",
    "Regular": "Reason for these months...",
    "High Season": "Reason for these months...",
    "Peak": "Reason for these months..."
  }},
  "revenue_impact": "Estimated annual revenue impact summary..."
}}

Adjust the periods, months, multipliers, and rates to best fit this specific location and property type.
Calculate each rate by multiplying the base rate by the multiplier. Return only the JSON object."""


def fetch_ical_occupancy(url):
    resp = requests.get(url, timeout=8)
    resp.raise_for_status()

    gcal = Calendar.from_ical(resp.content)

    today = date.today()
    one_year_ago = today - timedelta(days=365)

    blocked_days = defaultdict(set)

    for component in gcal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("DTSTART")
        dtend = component.get("DTEND")
        if not dtstart or not dtend:
            continue

        start = dtstart.dt
        end = dtend.dt
        if hasattr(start, "date"):
            start = start.date()
        if hasattr(end, "date"):
            end = end.date()

        d = start
        while d < end:
            if one_year_ago <= d < today:
                blocked_days[d.month].add(d)
            d += timedelta(days=1)

    total_days_by_month = defaultdict(int)
    d = one_year_ago
    while d < today:
        total_days_by_month[d.month] += 1
        d += timedelta(days=1)

    occupancy = {}
    for i, abbr in enumerate(MONTHS, 1):
        total = total_days_by_month.get(i, 0)
        blocked = len(blocked_days.get(i, set()))
        occupancy[abbr] = round(blocked / total * 100) if total > 0 else 0

    return occupancy


@app.route("/")
def index():
    return render_template("index.html", months=MONTHS)


@app.route("/analyze", methods=["POST"])
def analyze():
    location = request.form.get("location", "")
    property_type = request.form.get("property_type", "")
    base_rate = request.form.get("base_rate", "")
    currency = request.form.get("currency", "MXN")
    pricing_approach = request.form.get("pricing_approach", "flat")
    ical_url = request.form.get("ical_url", "").strip()

    ical_error = None
    occupancy_source = "manual"
    ical_occ = None

    if ical_url and Calendar is not None:
        try:
            ical_occ = fetch_ical_occupancy(ical_url)
            occupancy_source = "Airbnb calendar (last 12 months)"
        except Exception as e:
            ical_error = str(e)

    occupancy_parts = []
    occupancy_dict = {}
    for month in MONTHS:
        if ical_occ:
            val = str(ical_occ.get(month, 0))
        else:
            val = request.form.get(f"occupancy_{month}", "")
        occupancy_parts.append(f"{month}: {val}%")
        occupancy_dict[month] = val
    occupancy = ", ".join(occupancy_parts)

    prompt = PRICING_PROMPT.format(
        location=location,
        property_type=property_type,
        base_rate=base_rate,
        currency=currency,
        occupancy=occupancy,
        pricing_approach=pricing_approach,
        occupancy_source=occupancy_source,
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    recommendations = json.loads(raw)

    form_data = {
        "location": location,
        "property_type": property_type,
        "base_rate": base_rate,
        "currency": currency,
        "pricing_approach": pricing_approach,
        "occupancy_source": occupancy_source,
        "occupancy": occupancy_dict,
        "ical_error": ical_error,
    }

    return render_template("result.html", recommendations=recommendations, form_data=form_data)


if __name__ == "__main__":
    app.run(debug=True)
