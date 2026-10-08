"""
Dream2Build AI - Web Application Server
Converts custom homeowner inputs and multilingual prompts into realistic 3D concepts,
architectural floor plans, material quantities, and cost-optimized contractor dossiers.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import os
import re
import math
import db

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'dream2build_architectural_secret_key_2026')
db.init_db()

def detect_language_and_parse(prompt):
    """
    Multilingual NLP Entity Extractor for residential construction requirements.
    Supports English, Hindi, Telugu, Tamil, Spanish, French, German, and others.
    """
    text = prompt.strip()
    text_lower = text.lower()
    
    # Simple language hint detection
    lang = "English"
    if any(c in text for c in ['मुझे', 'बेडरूम', 'मंजिल', 'लाख', 'प्लॉट', 'कमरे']):
        lang = "Hindi (हिंदी)"
    elif any(c in text for c in ['నాకు', 'ప్లాట్', 'అంతస్తు', 'లక్షలు', 'గదులు']):
        lang = "Telugu (తెలుగు)"
    elif any(c in text for c in ['எனக்கு', 'அடுக்கு', 'படுக்கையறை', 'லட்சம்']):
        lang = "Tamil (தமிழ்)"
    elif any(w in text_lower for w in ['casa', 'habitaciones', 'baños', 'pisos', 'terreno']):
        lang = "Spanish (Español)"
    elif any(w in text_lower for w in ['maison', 'chambres', 'salles', 'étages', 'terrain']):
        lang = "French (Français)"
    elif any(w in text_lower for w in ['haus', 'zimmer', 'schlafzimmer', 'etagen', 'grundstück']):
        lang = "German (Deutsch)"

    # Spoken number words mapping for voice recognition
    WORD_TO_DIGIT = {
        'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6',
        'twenty': '20', 'thirty': '30', 'forty': '40', 'fifty': '50', 'sixty': '60',
        'एक': '1', 'दो': '2', 'तीन': '3', 'चार': '4', 'पाँच': '5', 'पांच': '5', 'छह': '6',
        'तीस': '30', 'चालीस': '40', 'पचास': '50',
        'ఒకటి': '1', 'రెండు': '2', 'మూడు': '3', 'నాలుగు': '4', 'ఐదు': '5',
        'uno': '1', 'dos': '2', 'tres': '3', 'cuatro': '4', 'cinco': '5',
        'treinta': '30', 'cuarenta': '40', 'cincuenta': '50'
    }
    for word, digit in WORD_TO_DIGIT.items():
        text_lower = re.sub(rf'\b{word}\b', digit, text_lower)

    # Plot dimensions (e.g. 30x40, 40*60, 30 by 40, 30 × 40, 30 गुणा 40, 30*40)
    plot_match = re.search(r'(\d{2,3})\s*(?:x|\*|by|×|गुणा|గుణకారం|de|sur)\s*(\d{2,3})', text_lower)
    if plot_match:
        w = int(plot_match.group(1))
        l = int(plot_match.group(2))
    else:
        # Check single square footage: e.g. 1200 sqft / sq.ft
        sqft_match = re.search(r'(\d{3,5})\s*(?:sqft|sq\.ft|वर्ग\s*फुट|చదరపు)', text_lower)
        if sqft_match:
            total_sq = int(sqft_match.group(1))
            w = int(math.sqrt(total_sq * 0.75))
            l = int(total_sq / max(w, 1))
        else:
            w, l = 30, 40

    # Bedrooms: 3 bhk, 3 bed, 3 bedroom, 3 बेडरूम, 3 గదులు, 3 hab, 3 chambres
    bed_match = re.search(r'(\d+)\s*(?:bhk|bed|bedroom|kamre|कमरे|बेडरूम|గదులు|படுக்கை|hab|chambre|zimmer)', text_lower)
    beds = max(1, min(6, int(bed_match.group(1)))) if bed_match else 3

    # Bathrooms: 2 bath, 2 bathroom, 2 बाथरूम, 2 baño, 2 salles de bain
    bath_match = re.search(r'(\d+)\s*(?:bath|bathroom|बाथरूम|స్నానపు|baño|douche|bad)', text_lower)
    baths = max(1, min(5, int(bath_match.group(1)))) if bath_match else 2

    # Floors: 2 floor, 2 story, 2 storey, 2 मंजिल, 2 అంతస్తు, 2 pisos, 2 étages
    floor_match = re.search(r'(\d+)\s*(?:floor|story|storey|मंजिल|అంతస్తు|அடுக்கு|piso|étage|etage)', text_lower)
    floors = max(1, min(3, int(floor_match.group(1)))) if floor_match else 2

    # Home office / study
    has_office = any(w in text_lower for w in ['office', 'study', 'work', 'दफ्तर', 'ఆఫీస్', 'ऑफिस', 'bureau', 'oficina'])

    # Parking cars
    parking_match = re.search(r'(\d+)\s*(?:car|parking|garage|गाड़ी|కార్|voiture|coche|auto)', text_lower)
    cars = max(0, min(3, int(parking_match.group(1)))) if parking_match else (2 if 'car' in text_lower or 'parking' in text_lower else 1)

    # Budget in Lakhs / Millions
    budget_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|l|लाख|లక్ష|லட்சம்|lac)', text_lower)
    if budget_match:
        budget_lakhs = float(budget_match.group(1))
    else:
        # Check raw number in thousands or millions
        raw_num = re.search(r'(?:₹|rs\.?|\$)\s*(\d{2,8})', text_lower)
        if raw_num:
            val = float(raw_num.group(1))
            budget_lakhs = val / 100000.0 if val > 100000 else val
        else:
            budget_lakhs = 35.0

    return {
        "detected_language": lang,
        "width": w,
        "length": l,
        "floors": floors,
        "bedrooms": beds,
        "bathrooms": baths,
        "has_office": has_office,
        "parking_cars": cars,
        "budget_lakhs": budget_lakhs,
        "style": "Modern Minimalist",
        "priority": "Natural Daylight & Cross-Ventilation",
        "orientation": "North-East Facing"
    }

def synthesize_custom_home(p):
    """
    Parametric architecture & civil takeoff engine that generates
    a bespoke, realistic 3D spatial layout, 2D blueprint, BOQ, and budget curves.
    """
    plot_w = max(20, min(100, int(p.get('width', 30))))
    plot_l = max(25, min(120, int(p.get('length', 40))))
    floors = max(1, min(3, int(p.get('floors', 2))))
    beds = max(1, min(6, int(p.get('bedrooms', 3))))
    baths = max(1, min(5, int(p.get('bathrooms', 2))))
    has_office = bool(p.get('has_office', True))
    cars = max(0, min(3, int(p.get('parking_cars', 2))))
    budget_lakhs = float(p.get('budget_lakhs', 35.0))
    style = p.get('style', 'Modern Minimalist')
    orientation = p.get('orientation', 'North-East Facing')

    plot_sqft = plot_w * plot_l
    coverage_ratio = 0.72  # Standard residential coverage allowing setbacks
    ground_sqft = int(plot_sqft * coverage_ratio)
    upper_sqft = int(ground_sqft * 0.90) if floors >= 2 else 0
    third_sqft = int(ground_sqft * 0.75) if floors >= 3 else 0
    total_built_up = ground_sqft + (upper_sqft * (floors - 1 if floors <= 2 else 1)) + third_sqft

    # 1. Spatial Room Allocation with Coordinates & Dimensions
    # Ground Floor Rooms
    ground_rooms = []
    
    # Living Room (Scaled to ~22% of ground floor)
    liv_w = round(plot_w * 0.52, 1)
    liv_l = round(plot_l * 0.35, 1)
    liv_area = int(liv_w * liv_l)
    ground_rooms.append({
        "id": "living",
        "name": "Living Lounge & Foyer",
        "dims": f"{liv_w}' × {liv_l}'",
        "sqft": liv_area,
        "pct": round((liv_area / total_built_up) * 100, 1),
        "floor": 1,
        "x": 2, "y": 0, "z": 2, "w": liv_w, "l": liv_l, "h": 10,
        "daylight": 95,
        "finish": "Vitrified Italian Marble Finish",
        "masonry": f"~{int(liv_area * 11)} AAC Blocks",
        "furniture": ["L-Shape Designer Sofa", "Coffee Table", "Media Console TV", "Accent Armchair"]
    })

    # Kitchen & Dining (Scaled to ~18% of ground floor)
    kit_w = round(plot_w * 0.42, 1)
    kit_l = round(plot_l * 0.32, 1)
    kit_area = int(kit_w * kit_l)
    ground_rooms.append({
        "id": "kitchen",
        "name": "Modular Kitchen & Dining",
        "dims": f"{kit_w}' × {kit_l}'",
        "sqft": kit_area,
        "pct": round((kit_area / total_built_up) * 100, 1),
        "floor": 1,
        "x": liv_w + 3, "y": 0, "z": 2, "w": kit_w, "l": kit_l, "h": 10,
        "daylight": 88,
        "finish": "Anti-Stain Quartz & Matte Tiles",
        "masonry": f"~{int(kit_area * 10)} AAC Blocks",
        "furniture": ["Kitchen Island Counter with Sink", "6-Seater Dining Table", "Pantry Cabinet"]
    })

    # Car Porch
    porch_w = 16 if cars >= 2 else (11 if cars == 1 else 8)
    porch_l = 15 if cars >= 2 else 12
    porch_area = porch_w * porch_l
    ground_rooms.append({
        "id": "porch",
        "name": f"Covered Car Porch ({cars} Car{'s' if cars > 1 else ''})",
        "dims": f"{porch_w}' × {porch_l}'",
        "sqft": porch_area,
        "pct": round((porch_area / total_built_up) * 100, 1),
        "floor": 1,
        "x": 2, "y": 0, "z": liv_l + 3, "w": porch_w, "l": porch_l, "h": 10,
        "daylight": 100,
        "finish": "Heavy-Duty Paver Cobblestone",
        "masonry": "RCC Structural Pillar Frame",
        "furniture": [f"Parked Vehicle ({cars} slots)", "EV Charging Station"]
    })

    # Ground Floor Bedroom (Guest bedroom if multi-floor, or Bed 1)
    g_bed_w = round(plot_w * 0.40, 1)
    g_bed_l = round(plot_l * 0.28, 1)
    g_bed_area = int(g_bed_w * g_bed_l)
    ground_rooms.append({
        "id": "g_bed",
        "name": "Guest Bedroom (Ground)" if floors > 1 else "Primary Bedroom",
        "dims": f"{g_bed_w}' × {g_bed_l}'",
        "sqft": g_bed_area,
        "pct": round((g_bed_area / total_built_up) * 100, 1),
        "floor": 1,
        "x": liv_w + 3, "y": 0, "z": kit_l + 3, "w": g_bed_w, "l": g_bed_l, "h": 10,
        "daylight": 84,
        "finish": "Hardwood Teak Flooring",
        "masonry": f"~{int(g_bed_area * 11)} AAC Blocks",
        "furniture": ["Queen Bed with Headboard", "Nightstands", "Built-in Wardrobe"]
    })

    # Ground Bathroom
    g_bath_w, g_bath_l = 7.5, 5.5
    g_bath_area = int(g_bath_w * g_bath_l)
    ground_rooms.append({
        "id": "g_bath",
        "name": "Guest Bathroom & Powder Room",
        "dims": f"{g_bath_w}' × {g_bath_l}'",
        "sqft": g_bath_area,
        "pct": round((g_bath_area / total_built_up) * 100, 1),
        "floor": 1,
        "x": liv_w + 3, "y": 0, "z": kit_l + 3 + g_bed_l + 1.5,
        "w": g_bath_w, "l": g_bath_l, "h": 10,
        "daylight": 78,
        "finish": "Ceramic Anti-Skid Tiles",
        "masonry": f"~{int(g_bath_area * 12)} AAC Blocks",
        "furniture": ["Walk-in Shower Cubicle", "Wall-Hung Vanity Counter", "Water Closet"]
    })

    # First Floor Rooms (if floors >= 2)
    first_rooms = []
    if floors >= 2:
        # Master Bedroom Suite (with attached bath & balcony)
        m_bed_w = round(plot_w * 0.50, 1)
        m_bed_l = round(plot_l * 0.34, 1)
        m_bed_area = int(m_bed_w * m_bed_l)
        first_rooms.append({
            "id": "m_bed",
            "name": "Master Bedroom Suite",
            "dims": f"{m_bed_w}' × {m_bed_l}'",
            "sqft": m_bed_area,
            "pct": round((m_bed_area / total_built_up) * 100, 1),
            "floor": 2,
            "x": 2, "y": 10, "z": 2, "w": m_bed_w, "l": m_bed_l, "h": 10,
            "daylight": 96,
            "finish": "Acoustic Warm Oak Parquet",
            "masonry": f"~{int(m_bed_area * 11)} AAC Blocks",
            "furniture": ["King Size Designer Bed", "Walk-in Dressing Closet", "Lounge Chairs"]
        })

        # Attached Master Bathroom
        m_bath_w, m_bath_l = 8.5, 6.0
        m_bath_area = int(m_bath_w * m_bath_l)
        first_rooms.append({
            "id": "m_bath",
            "name": "Master En-Suite Bathroom",
            "dims": f"{m_bath_w}' × {m_bath_l}'",
            "sqft": m_bath_area,
            "pct": round((m_bath_area / total_built_up) * 100, 1),
            "floor": 2,
            "x": 2, "y": 10, "z": m_bed_l + 3, "w": m_bath_w, "l": m_bath_l, "h": 10,
            "daylight": 85,
            "finish": "Seamless Porcelain & Glass",
            "masonry": f"~{int(m_bath_area * 12)} AAC Blocks",
            "furniture": ["Frameless Glass Rain Shower", "Double Vanity Sink", "Smart WC"]
        })

        # Master Balcony Deck
        balc_w = round(m_bed_w * 0.85, 1)
        balc_l = 5.5
        balc_area = int(balc_w * balc_l)
        first_rooms.append({
            "id": "balcony",
            "name": "Scenic Balcony Deck",
            "dims": f"{balc_w}' × {balc_l}'",
            "sqft": balc_area,
            "pct": round((balc_area / total_built_up) * 100, 1),
            "floor": 2,
            "x": 2, "y": 10, "z": m_bed_l + 3 + m_bath_l + 1.5, "w": balc_w, "l": balc_l, "h": 10,
            "daylight": 100,
            "finish": "Toughened Glass Railing & Weather Deck",
            "masonry": "Parapet & Stainless Steel Rail",
            "furniture": ["Coffee Bistro Table", "Planters with Greenery"]
        })

        # Bedroom 2 (Upper Floor)
        bed2_w = round(plot_w * 0.42, 1)
        bed2_l = round(plot_l * 0.30, 1)
        bed2_area = int(bed2_w * bed2_l)
        first_rooms.append({
            "id": "bed2",
            "name": "Bedroom 2 (Family / Kids)",
            "dims": f"{bed2_w}' × {bed2_l}'",
            "sqft": bed2_area,
            "pct": round((bed2_area / total_built_up) * 100, 1),
            "floor": 2,
            "x": m_bed_w + 3, "y": 10, "z": 2, "w": bed2_w, "l": bed2_l, "h": 10,
            "daylight": 90,
            "finish": "Stain-Resistant Engineered Wood",
            "masonry": f"~{int(bed2_area * 11)} AAC Blocks",
            "furniture": ["Queen Bed", "Twin Study Desks", "Full Wardrobe"]
        })

        # Home Office or Bedroom 3
        if has_office:
            off_w = round(plot_w * 0.38, 1)
            off_l = round(plot_l * 0.26, 1)
            off_area = int(off_w * off_l)
            first_rooms.append({
                "id": "office",
                "name": "Executive Home Office & Library",
                "dims": f"{off_w}' × {off_l}'",
                "sqft": off_area,
                "pct": round((off_area / total_built_up) * 100, 1),
                "floor": 2,
                "x": m_bed_w + 3, "y": 10, "z": bed2_l + 3, "w": off_w, "l": off_l, "h": 10,
                "daylight": 94,
                "finish": "Acoustic Wooden Wall Panels & Desk",
                "masonry": f"~{int(off_area * 10)} AAC Blocks",
                "furniture": ["Executive L-Desk with Ergonomic Chair", "Bookcase Wall", "Conference Monitor"]
            })
        elif beds >= 3:
            bed3_w = round(plot_w * 0.38, 1)
            bed3_l = round(plot_l * 0.26, 1)
            bed3_area = int(bed3_w * bed3_l)
            first_rooms.append({
                "id": "bed3",
                "name": "Bedroom 3",
                "dims": f"{bed3_w}' × {bed3_l}'",
                "sqft": bed3_area,
                "pct": round((bed3_area / total_built_up) * 100, 1),
                "floor": 2,
                "x": m_bed_w + 3, "y": 10, "z": bed2_l + 3, "w": bed3_w, "l": bed3_l, "h": 10,
                "daylight": 88,
                "finish": "Vitrified Tiles",
                "masonry": f"~{int(bed3_area * 11)} AAC Blocks",
                "furniture": ["Double Bed", "Study Table", "Wardrobe"]
            })

        # Upper Common Bathroom (if baths >= 2)
        u_bath_w, u_bath_l = 7.5, 5.5
        u_bath_area = int(u_bath_w * u_bath_l)
        upper_z_offset = off_l if has_office else (round(plot_l * 0.26, 1) if beds >= 3 else 0)
        first_rooms.append({
            "id": "u_bath",
            "name": "Upper Floor Common Bathroom",
            "dims": f"{u_bath_w}' × {u_bath_l}'",
            "sqft": u_bath_area,
            "pct": round((u_bath_area / total_built_up) * 100, 1),
            "floor": 2,
            "x": m_bed_w + 3, "y": 10, "z": bed2_l + 3 + upper_z_offset + 1.5,
            "w": u_bath_w, "l": u_bath_l, "h": 10,
            "daylight": 80,
            "finish": "Glazed Ceramic Tiles",
            "masonry": f"~{int(u_bath_area * 12)} AAC Blocks",
            "furniture": ["Shower Stall", "Vanity Sink", "Water Closet"]
        })

    all_rooms = ground_rooms + first_rooms

    # 2. Dynamic Bill of Quantities (BOQ Takeoff)
    cement_bags = int(total_built_up * 0.443)
    steel_tonnes = round(total_built_up * 0.00259, 2)
    aac_blocks = int(total_built_up * 10.0)
    sand_cuft = int(total_built_up * 1.0)
    aggregate_cuft = int(total_built_up * 0.767)
    tiles_sqft = int(total_built_up * 0.89)
    paint_litres = int(total_built_up * 0.173)
    windows_count = max(4, int(beds * 2 + baths + 2))
    doors_count = max(3, int(beds + baths + 3))

    materials = [
        {"item": "Cement (Grade 53 OPC & PPC)", "quantity": cement_bags, "unit": "bags", "unit_price": 390, "total": cement_bags * 390, "category": "Civil"},
        {"item": "TMT Rebars (Fe 500D Treated Steel)", "quantity": steel_tonnes, "unit": "tonnes", "unit_price": 68000, "total": int(steel_tonnes * 68000), "category": "Structural"},
        {"item": "AAC Lightweight Blocks (High Thermal Mass)", "quantity": aac_blocks, "unit": "blocks", "unit_price": 42, "total": aac_blocks * 42, "category": "Masonry"},
        {"item": "Processed M-Sand (River Sand Substitute)", "quantity": sand_cuft, "unit": "cu.ft", "unit_price": 55, "total": sand_cuft * 55, "category": "Civil"},
        {"item": "Coarse Aggregate (20mm Blue Metal)", "quantity": aggregate_cuft, "unit": "cu.ft", "unit_price": 48, "total": aggregate_cuft * 48, "category": "Civil"},
        {"item": "Vitrified Floor Tiles (Anti-Skid 600×600mm)", "quantity": tiles_sqft, "unit": "sq.ft", "unit_price": 75, "total": tiles_sqft * 75, "category": "Finishing"},
        {"item": "Low-VOC Exterior & Interior Emulsion Paint", "quantity": paint_litres, "unit": "litres", "unit_price": 310, "total": paint_litres * 310, "category": "Finishing"},
        {"item": "UPVC Double-Glazed Soundproof Windows", "quantity": windows_count, "unit": "units", "unit_price": 14500, "total": windows_count * 14500, "category": "Openings"},
        {"item": "Flush Doors with Teak Veneer & Hardware", "quantity": doors_count, "unit": "units", "unit_price": 11200, "total": doors_count * 11200, "category": "Openings"}
    ]

    materials_base_cost = sum(m['total'] for m in materials)

    # 3. Dynamic Cost Range Calculation
    sqft_rate = 1850  # Average standard residential rate in INR
    estimated_cost = int(total_built_up * sqft_rate)
    min_cost = int(estimated_cost * 0.96)
    max_cost = int(estimated_cost * 1.05)
    target_budget = int(budget_lakhs * 100000)
    budget_buffer = target_budget - estimated_cost

    cost_breakdown = [
        {"category": "Civil & Structural Core", "amount": int(estimated_cost * 0.48), "pct": 48, "details": "Foundation, Columns, Slabs, AAC Masonry"},
        {"category": "Finishing & Architectural Interiors", "amount": int(estimated_cost * 0.26), "pct": 26, "details": "Tiles, Teakwood, Paints, Sanitary Fixtures"},
        {"category": "MEP (Plumbing & Electrical)", "amount": int(estimated_cost * 0.14), "pct": 14, "details": "Conduits, CPVC Lines, Modular Switchgear"},
        {"category": "Labor, Approvals & Site Setup", "amount": int(estimated_cost * 0.12), "pct": 12, "details": "Curing, Staging, Municipal Filings"}
    ]

    # 4. Dynamic Optimization Scenarios
    aac_opt_saving = int(aac_blocks * 2.3)
    aac_opt_scrap = round(aac_blocks * 0.00008, 1)
    steel_opt_saving = int(steel_tonnes * 14200)
    steel_opt_scrap = round(steel_tonnes * 0.38, 1)
    fly_ash_saving = int(cement_bags * 34)
    corridor_saving = int(total_built_up * 60)

    optimizations = [
        {
            "id": "aac_modular",
            "title": "Modular AAC Block Course Sizing",
            "desc": f"Aligns {aac_blocks:,} block courses to standard 600×200mm modules. Eliminates manual chiseling scrap.",
            "waste_saved": f"{aac_opt_scrap} tonnes scrap",
            "cost_saved": aac_opt_saving,
            "active": True
        },
        {
            "id": "rebar_scheduling",
            "title": "AI Linear Bar Bending Schedule (BBS)",
            "desc": f"Squeezes cutting of {steel_tonnes} tonnes steel to reduce commercial offcut scrap from 12% to under 4%.",
            "waste_saved": f"{steel_opt_scrap} tonnes steel",
            "cost_saved": steel_opt_saving,
            "active": True
        },
        {
            "id": "fly_ash_blend",
            "title": "Pozzolana Fly Ash Plastering Scheme",
            "desc": f"Blends non-structural mortar for {cement_bags} bags with fly-ash pozzolana, enhancing durability.",
            "waste_saved": "0.8 tonnes CO2 eq.",
            "cost_saved": fly_ash_saving,
            "active": True
        },
        {
            "id": "circulation_trim",
            "title": "Circulation & Dead Hallway Squeeze",
            "desc": f"Optimizes room transitions down to 6.8% circulation space, trimming redundant concrete slab pouring.",
            "waste_saved": "0.6 tonnes concrete",
            "cost_saved": corridor_saving,
            "active": False
        }
    ]

    return {
        "specs": {
            "plot_dimensions": f"{plot_w} × {plot_l} ft ({plot_sqft:,} sq.ft)",
            "built_up_area": f"{total_built_up:,} sq.ft",
            "floors": floors,
            "bedrooms": beds,
            "bathrooms": baths,
            "office": 1 if has_office else 0,
            "parking": f"{cars} car{'s' if cars > 1 else ''} ({porch_w}×{porch_l} ft porch)",
            "budget": f"₹{budget_lakhs} Lakhs",
            "budget_val": target_budget,
            "style": style,
            "priority": "Natural Daylight & Cross-Ventilation",
            "orientation": orientation
        },
        "rooms": {
            "ground": ground_rooms,
            "first": first_rooms,
            "all": all_rooms
        },
        "cost_range": {
            "min": f"₹{(min_cost/100000):.1f}L",
            "max": f"₹{(max_cost/100000):.1f}L",
            "estimated": estimated_cost,
            "target_budget": target_budget,
            "buffer": budget_buffer,
            "breakdown": cost_breakdown
        },
        "materials": materials,
        "materials_base_cost": materials_base_cost,
        "optimizations": optimizations
    }

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html',
                           user_name=session.get('user_name', 'Lead Architect'),
                           user_email=session.get('user_email', ''))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        user, err = db.verify_user(email, password)
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error=err)
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match.")
        user, err = db.create_user(name, email, password)
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            return redirect(url_for('index'))
        else:
            return render_template('register.html', error=err)
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/auth/status')
def auth_status():
    if 'user_id' in session:
        return jsonify({
            "logged_in": True,
            "user": {
                "id": session.get('user_id'),
                "name": session.get('user_name'),
                "email": session.get('user_email')
            }
        })
    return jsonify({"logged_in": False})

@app.route('/api/parse-prompt', methods=['POST'])
def parse_prompt_endpoint():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized. Please log in."}), 401
    data = request.get_json() or {}
    prompt = data.get('prompt', '')
    parsed = detect_language_and_parse(prompt)
    return jsonify({
        "status": "success",
        "parsed": parsed
    })

@app.route('/api/synthesize', methods=['POST'])
def synthesize_endpoint():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized. Please log in."}), 401
    data = request.get_json() or {}
    
    # If natural prompt was passed, parse it first
    if 'prompt' in data and data['prompt'] and not data.get('skip_prompt_parse'):
        params = detect_language_and_parse(data['prompt'])
        # Allow explicit overrides
        for k, v in data.items():
            if k != 'prompt':
                params[k] = v
    else:
        params = data
        
    result = synthesize_custom_home(params)
    return jsonify({
        "status": "success",
        "data": result
    })

@app.route('/api/optimize', methods=['POST'])
def calculate_optimization():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized. Please log in."}), 401
    data = request.get_json() or {}
    active_opts = data.get('active_optimizations', [])
    opts_list = data.get('optimizations_list', [])
    base_cost = data.get('base_cost', 3385000)
    
    total_savings = 0
    total_waste_tonnes = 0.0
    
    for opt in opts_list:
        if opt['id'] in active_opts:
            total_savings += opt.get('cost_saved', 0)
            waste_str = opt.get('waste_saved', '')
            if 'tonnes' in waste_str:
                try:
                    val = float(waste_str.split()[0])
                    total_waste_tonnes += val
                except ValueError:
                    pass

    optimized_cost = base_cost - total_savings
    savings_pct = round((total_savings / base_cost) * 100, 1) if base_cost else 0.0
    
    return jsonify({
        "status": "success",
        "base_cost": base_cost,
        "optimized_cost": optimized_cost,
        "total_savings": total_savings,
        "savings_percentage": savings_pct,
        "waste_diverted_tonnes": round(total_waste_tonnes, 2)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Dream2Build AI server on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
