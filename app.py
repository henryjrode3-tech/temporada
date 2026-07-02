import os
import json
import anthropic
from flask import Flask, render_template, request
from dotenv import load_dotenv

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

    occupancy_parts = []
    for month in MONTHS:
        val = request.form.get(f"occupancy_{month}", "")
        occupancy_parts.append(f"{month}: {val}%")
    occupancy = ", ".join(occupancy_parts)

    prompt = PRICING_PROMPT.format(
        location=location,
        property_type=property_type,
        base_rate=base_rate,
        currency=currency,
        occupancy=occupancy,
        pricing_approach=pricing_approach,
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
        "occupancy": dict(zip(MONTHS, [request.form.get(f"occupancy_{m}", "") for m in MONTHS])),
    }

    return render_template("result.html", recommendations=recommendations, form_data=form_data)


if __name__ == "__main__":
    app.run(debug=True)
