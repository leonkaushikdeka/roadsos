import asyncio
import csv
import json
import logging
import os
from pathlib import Path
from sqlalchemy import text
from app.database import engine, async_session, init_db
from app.models.emergency_service import EmergencyService

logger = logging.getLogger(__name__)

TN_HOSPITALS = [
    {"name": "Rajiv Gandhi Government General Hospital", "type": "hospital", "grade": 1, "lat": 13.0800, "lng": 80.2700, "phone": "044-25305000", "address": "Park Town, Chennai", "icu": True, "vent": True, "blood": True, "trauma": True, "beds": 3000},
    {"name": "Apollo Hospital Chennai", "type": "hospital", "grade": 1, "lat": 12.9830, "lng": 80.2110, "phone": "044-28290200", "address": "Greams Road, Chennai", "icu": True, "vent": True, "blood": True, "trauma": True, "beds": 1000},
    {"name": "Stanley Medical College Hospital", "type": "hospital", "grade": 1, "lat": 13.0980, "lng": 80.2650, "phone": "044-25281345", "address": "Old Jail Road, Chennai", "icu": True, "vent": True, "blood": True, "trauma": True, "beds": 2000},
    {"name": "Christian Medical College Vellore", "type": "hospital", "grade": 1, "lat": 12.9210, "lng": 79.1480, "phone": "0416-2282000", "address": "Vellore", "icu": True, "vent": True, "blood": True, "trauma": True, "beds": 3000},
    {"name": "Government Medical College & Hospital Coimbatore", "type": "hospital", "grade": 2, "lat": 11.0200, "lng": 76.9700, "phone": "0422-2301393", "address": "Coimbatore", "icu": True, "vent": True, "blood": True, "trauma": True, "beds": 1500},
    {"name": "Madurai Medical College", "type": "hospital", "grade": 2, "lat": 9.9200, "lng": 78.1200, "phone": "0452-2530535", "address": "Madurai", "icu": True, "vent": True, "blood": True, "trauma": False, "beds": 2000},
    {"name": "Kauvery Hospital Chennai", "type": "hospital", "grade": 1, "lat": 13.0100, "lng": 80.2100, "phone": "044-40002000", "address": "Alwarpet, Chennai", "icu": True, "vent": True, "blood": True, "trauma": True, "beds": 500},
    {"name": "MIOT International", "type": "hospital", "grade": 1, "lat": 13.0000, "lng": 80.2200, "phone": "044-42002288", "address": "Manapakkam, Chennai", "icu": True, "vent": True, "blood": True, "trauma": True, "beds": 600},
    {"name": "SRM Medical College Hospital", "type": "hospital", "grade": 2, "lat": 12.8200, "lng": 80.0400, "phone": "044-47437500", "address": "SRM Nagar, Chengalpattu", "icu": True, "vent": True, "blood": True, "trauma": False, "beds": 800},
    {"name": "Meenakshi Mission Hospital Madurai", "type": "hospital", "grade": 2, "lat": 9.9400, "lng": 78.0900, "phone": "0452-2587024", "address": "Madurai", "icu": True, "vent": True, "blood": True, "trauma": False, "beds": 600},
]

TN_AMBULANCES = [
    {"name": "108 EMRI Ambulance Hub - Chennai Central", "type": "ambulance", "lat": 13.0827, "lng": 80.2707, "phone": "108", "address": "Chennai Central", "beds": 0},
    {"name": "108 EMRI Ambulance Hub - Tambaram", "type": "ambulance", "lat": 12.9249, "lng": 80.1000, "phone": "108", "address": "Tambaram, Chennai", "beds": 0},
    {"name": "108 EMRI Ambulance Hub - Vellore", "type": "ambulance", "lat": 12.9200, "lng": 79.1500, "phone": "108", "address": "Vellore", "beds": 0},
    {"name": "108 EMRI Ambulance Hub - Coimbatore", "type": "ambulance", "lat": 11.0200, "lng": 76.9700, "phone": "108", "address": "Coimbatore", "beds": 0},
    {"name": "108 EMRI Ambulance Hub - Madurai", "type": "ambulance", "lat": 9.9200, "lng": 78.1200, "phone": "108", "address": "Madurai", "beds": 0},
    {"name": "108 EMRI Ambulance Hub - Trichy", "type": "ambulance", "lat": 10.7900, "lng": 78.7000, "phone": "108", "address": "Trichy", "beds": 0},
    {"name": "108 EMRI Ambulance Hub - Salem", "type": "ambulance", "lat": 11.6600, "lng": 78.1400, "phone": "108", "address": "Salem", "beds": 0},
    {"name": "108 EMRI Ambulance Hub - Tirunelveli", "type": "ambulance", "lat": 8.7300, "lng": 77.7000, "phone": "108", "address": "Tirunelveli", "beds": 0},
    {"name": "108 EMRI Ambulance Hub - Hosur", "type": "ambulance", "lat": 12.7200, "lng": 77.8300, "phone": "108", "address": "Hosur", "beds": 0},
    {"name": "108 EMRI Ambulance Hub - Kanyakumari", "type": "ambulance", "lat": 8.0800, "lng": 77.5400, "phone": "108", "address": "Kanyakumari", "beds": 0},
]

TN_POLICE = [
    {"name": "Chennai City Police HQ", "type": "police", "lat": 13.0800, "lng": 80.2600, "phone": "100", "address": "Chennai"},
    {"name": "Vellore District Police", "type": "police", "lat": 12.9200, "lng": 79.1300, "phone": "100", "address": "Vellore"},
    {"name": "Coimbatore City Police", "type": "police", "lat": 11.0100, "lng": 76.9600, "phone": "100", "address": "Coimbatore"},
    {"name": "Madurai City Police", "type": "police", "lat": 9.9300, "lng": 78.1100, "phone": "100", "address": "Madurai"},
    {"name": "Trichy District Police", "type": "police", "lat": 10.8000, "lng": 78.6900, "phone": "100", "address": "Trichy"},
    {"name": "Salem District Police", "type": "police", "lat": 11.6500, "lng": 78.1600, "phone": "100", "address": "Salem"},
    {"name": "NH-44 Highway Patrol - Krishnagiri", "type": "police", "lat": 12.5200, "lng": 78.2100, "phone": "100", "address": "Krishnagiri"},
    {"name": "NH-66 Highway Patrol - Tindivanam", "type": "police", "lat": 12.2400, "lng": 79.6500, "phone": "100", "address": "Tindivanam"},
    {"name": "Chengalpattu District Police", "type": "police", "lat": 12.7000, "lng": 79.9800, "phone": "100", "address": "Chengalpattu"},
    {"name": "Kanyakumari District Police", "type": "police", "lat": 8.0800, "lng": 77.5400, "phone": "100", "address": "Kanyakumari"},
]

TN_BLOOD_BANKS = [
    {"name": "Jeevan Blood Bank Chennai", "type": "blood_bank", "lat": 13.0600, "lng": 80.2500, "phone": "044-28157978", "address": "Chennai"},
    {"name": "Indian Red Cross Blood Bank Chennai", "type": "blood_bank", "lat": 13.0700, "lng": 80.2600, "phone": "044-25302222", "address": "Chennai"},
    {"name": "Vellore Blood Centre", "type": "blood_bank", "lat": 12.9100, "lng": 79.1400, "phone": "0416-2263100", "address": "Vellore"},
    {"name": "Coimbatore Blood Bank", "type": "blood_bank", "lat": 11.0200, "lng": 76.9800, "phone": "0422-2233441", "address": "Coimbatore"},
    {"name": "Madurai Blood Bank", "type": "blood_bank", "lat": 9.9300, "lng": 78.1200, "phone": "0452-2521444", "address": "Madurai"},
]

# ─── Protocol data: EN + HI + TA + BN + SI ───

PROTOCOL_DATA = [
    # English
    {"source": "WHO_2023", "language": "en", "type": "bleeding_control",
     "text": "Apply firm direct pressure to the wound using a clean cloth or bandage. Maintain pressure for at least 10-15 minutes. Do not remove embedded objects. If blood soaks through, add more cloth on top — do not remove the first layer. Elevate the injured area if possible. Call 108 or 112 for emergency transport.",
     "tags": ["bleeding", "hemorrhage", "pressure", "first-aid"]},
    {"source": "Red_Cross_IN_2022", "language": "en", "type": "cpr",
     "text": "Place the person on their back on a firm surface. Kneel beside them. Place the heel of one hand on the center of the chest (between the nipples). Place your other hand on top, interlocking fingers. Keep your elbows straight and shoulders directly above your hands. Compress the chest at least 2 inches deep at a rate of 100-120 compressions per minute. Allow full chest recoil between compressions. Continue until emergency services arrive or the person shows signs of life.",
     "tags": ["cpr", "cardiac", "resuscitation", "breathing"]},
    {"source": "ATLS_10th", "language": "en", "type": "spinal_precautions",
     "text": "Do NOT move the patient unless there is immediate danger (fire, flooding, unstable structure). Maintain manual in-line stabilization of the head and neck. Keep the patient's head, neck, and spine aligned at all times. If the patient must be moved, use a log-roll technique with at least 4 persons. Apply a rigid cervical collar if available.",
     "tags": ["spinal", "neck", "fracture", "immobilization"]},
    {"source": "WHO_2023", "language": "en", "type": "shock_management",
     "text": "Lay the person down on their back. Elevate the legs about 12 inches (30 cm) unless you suspect spinal injury. Keep the person warm with a blanket or jacket. Do not give anything to eat or drink. Monitor breathing and consciousness. Turn the person on their side if they vomit or bleed from the mouth.",
     "tags": ["shock", "unconscious", "fainting"]},
    {"source": "Indian_Red_Cross_2022", "language": "en", "type": "fracture_management",
     "text": "Do not attempt to realign bones or push them back. Immobilize the injured area using splints — boards, rolled newspapers, or sturdy cardboard. Pad the splint with cloth. Tie splint above and below the injury site, not directly over it. Check for circulation beyond the injury every 10 minutes. Apply ice pack wrapped in cloth to reduce swelling.",
     "tags": ["fracture", "bone", "splint", "immobilization"]},
    {"source": "WHO_2023", "language": "en", "type": "recovery_position",
     "text": "Roll the person onto their side. Tilt the head back to keep the airway open. Bend the top leg at the knee and hip to stabilize the body. Monitor breathing continuously.",
     "tags": ["recovery", "position", "airway", "unconscious"]},
    {"source": "WHO_2023", "language": "en", "type": "burns_first_aid",
     "text": "Cool the burn under cool running water for at least 20 minutes. Do not use ice, butter, or ointments. Remove clothing or jewelry near the burn if possible. Cover with a sterile non-stick dressing. Call 108 for severe burns.",
     "tags": ["burns", "cooling", "first-aid", "thermal"]},

    # Hindi
    {"source": "WHO_2023", "language": "hi", "type": "bleeding_control",
     "text": "एक साफ कपड़े या पट्टी से घाव पर मजबूत सीधा दबाव डालें। कम से कम 10-15 मिनट तक दबाव बनाए रखें। घाव में फंसी वस्तुओं को न हटाएं। अगर खून निकलता रहे तो ऊपर और कपड़ा रखें — पहली परत न हटाएं। यदि संभव हो तो घायल भाग को ऊपर उठाएं। एम्बुलेंस के लिए 108 या 112 पर कॉल करें।",
     "tags": ["bleeding", "hemorrhage", "pressure", "first-aid", "hindi"]},
    {"source": "ATLS_10th", "language": "hi", "type": "cpr",
     "text": "व्यक्ति को सख्त सतह पर पीठ के बल लिटाएं। उनके बगल में घुटने टेकें। एक हाथ की एड़ी को छाती के केंद्र (निपल्स के बीच) पर रखें। दूसरा हाथ ऊपर रखें और अंगुलियों को आपस में फंसा लें। कोहनियां सीधी रखें और कंधे सीधे हाथों के ऊपर हों। छाती को कम से कम 2 इंच गहरा दबाएं, 100-120 दबाव प्रति मिनट की दर से। एम्बुलेंस आने तक जारी रखें।",
     "tags": ["cpr", "cardiac", "resuscitation", "hindi"]},
    {"source": "ATLS_10th", "language": "hi", "type": "spinal_precautions",
     "text": "रोगी को इससे पहले कि तुरंत खतरा (आग, बाढ़, अस्थिर संरचना) न हो, न हिलाएं। सिर और गर्दन को अपने हाथों से सीधा और स्थिर रखें। रोगी का सिर, गर्दन और रीढ़ हमेशा एक सीध में रखें।",
     "tags": ["spinal", "neck", "fracture", "immobilization", "hindi"]},
    {"source": "WHO_2023", "language": "hi", "type": "shock_management",
     "text": "व्यक्ति को पीठ के बल लिटाकर ज़मीन पर रखें। पैरों को लगभग 12 इंच (30 सेमी) ऊपर उठाएं जब तक रीढ़ की चोट का संदेह न हो। गर्म कंबल या जैकेट से गर्म रखें। कुछ भी खाने या पीने की चीज़ न दें। साँस और चेतना पर नज़र रखें।",
     "tags": ["shock", "unconscious", "fainting", "hindi"]},
    {"source": "Indian_Red_Cross_2022", "language": "hi", "type": "fracture_management",
     "text": "हड्डियों को वापस सीधा करने की कोशिश न करें। टुकड़ों, किताबों, या मोटे कागज़ से चोटिल हिस्से को पकड़कर रोकें। कपड़े से ढकें। पट्टी चोट के ऊपर और नीचे बाँधें, सीधे ऊपर नहीं। हर 10 मिनट में खून का रंग जाँचें।",
     "tags": ["fracture", "bone", "splint", "immobilization", "hindi"]},

    # Tamil
    {"source": "translated_draft", "language": "ta", "type": "bleeding_control",
     "text": "ஒரு சுத்தமான துணியோடு காயத்தில் நெடுங்க அழுத்தம் வைக்கவும். குறைந்தது 10-15 நிமிடம் அழுத்தத்தை வைத்திருக்கவும். உடலில் ஆழமாக உள்ள பொருள்களை எடுக்க வேண்டாம். இரத்தம் வரவேற்கிறதென்றால், மேலே இன்னொரு துணியை வைக்கவும் — முதல் அடுக்கை நீக்க வேண்டாம். சாத்தியமானதென்றால், காயப்பட்ட பகுதியை மேற்குத் திருப்பவும். அவசர சேவைக்கு 108 அல்லது 112 என்பதற்கு அழைக்கவும்.",
     "tags": ["bleeding", "hemorrhage", "pressure", "first-aid", "tamil"]},
    {"source": "translated_draft", "language": "ta", "type": "cpr",
     "text": "நபரை ஒரு வச்ச மேற்பரப்பில் அமுக்கிய இடத்தில் கீழே நாட்டுகள். அவர்கள் பக்கத்தில் கெம்ப்போட்டு. ஒரு கையின் முட்கையை மார்புக்குள் இடம் வைக்கவும். மற்றொரு கையை மேல் வைத்து விரல்களை ஒன்றிணைக்கவும். மெத்தி நோக்கி, கண்கள் நேரடியாக மார்புகள் மீது. குறைந்தது 2 அங்குகள் ஆழமாக, மினிட்டுக்கு 100-120 அழுத்தங்கள் வேகத்தால் அழுத்தவும். சூழ்ச்சி முழுக்க சுமையாக அனுமதிக்கவும்.",
     "tags": ["cpr", "cardiac", "resuscitation", "tamil"]},
    {"source": "translated_draft", "language": "ta", "type": "spinal_precautions",
     "text": "பெரும் ஆபத்து இல்லை இல்லன்னால் நோயாளியை நகர்த்த வேண்டாம். தலையும் கழுத்தும் நேர்மையாகப் பற்றிக்கொள்ளவும். உடல் நேர்மையாக இருக்கலாம். முயற்சிக்கப்பட்டால், குறைந்தது 4 பேர் முடிவுகள் மாற்றுக.",
     "tags": ["spinal", "neck", "fracture", "immobilization", "tamil"]},
    {"source": "translated_draft", "language": "ta", "type": "shock_management",
     "text": "நபரை அடியில் அழுத்துக்குள் நாட்டவும். கால்களை அருகிலுள்ள கண்ணாடி 12 அடி (30 செ.மீ) உயரத்தில் ஏந்தவும். மூச்சு கண்டுபிடிக்கப்பட்டால் பாதிக்கப்படும் என்று யோசிக்கப்படாத வரை. பொதியும் பட்டணியோ அல்லது கடிதமாக இருக்கவும். எதுவும் சாப்பிடவோ குடிநீர் பானம் எனவும் வைத்திருக்கவும்.",
     "tags": ["shock", "unconscious", "fainting", "tamil"]},
    {"source": "translated_draft", "language": "ta", "type": "recovery_position",
     "text": "நபரை அடியில் பக்கத்தில் உருளுக. தலையை பின்னால் கரைத்துக்கொள்ளவும் வயிற்றை திறமையாக வைத்திருக்கலாம். மேல் காலையை மாற்று திருப்பதில் நிறுத்தவும்.",
     "tags": ["recovery", "position", "airway", "tamil"]},
    {"source": "translated_draft", "language": "ta", "type": "fracture_management",
     "text": "எலும்புகளை மீட்டு சீரமைக்க முயற்சிக்க வேண்டாம். பலகைகள், துரல்கள் அல்லது நிறுவப்பட்ட சீரமைப்பாளர்கள் மூலம் உடற்பகுதியை நிறுத்தவும். விரல் மீது நேரடியாக பட்டணிக்க வேண்டாம். சாத்தியமானதென்றால் அழுத்தத்தை அழித்து கொள்.",
     "tags": ["fracture", "bone", "splint", "immobilization", "tamil"]},

    # Bengali
    {"source": "translated_draft", "language": "bn", "type": "bleeding_control",
     "text": "একটি পরিষ্কার বেঁথা বা তারার দিয়ে ক্ষতস্থানে শক্তিশালী সরল চাপ দিন। অন্তত 10-15 মিনিট চাপ ধরে রাখুন। বস্তু গভীরে পড়ে থাকলে তুলে আনবেন না। রক্ত জ্বলে থাকলে, প্রথম স্তর সরান না — এর উপর আরও বেঁথা রাখুন। সম্ভব হলে আঘাতপ্রাপ্ত অংশটুকু তুলে ধরুন। জরুরি পরিষেবার জন্য ১০৮ বা ১১২ তে কল করুন।",
     "tags": ["bleeding", "hemorrhage", "pressure", "first-aid", "bengali"]},
    {"source": "translated_draft", "language": "bn", "type": "cpr",
     "text": "ব্যক্তিকে একটি শক্তিশালী তলায় পিঠ দিয়ে ওপাশে রাখুন। তাদের পাশে হাঁটু দিন। একটি হাতের গুটি বুকের মাঝখানে (কন্যা মাঝে) রাখুন। অন্য হাতটি উপরে রাখুন এবং আঙুলগুলোকে জড়িয়ে দিন। কোল সরাসরি উপরে রাখুন। বুকের মধ্যে কমপক্ষে 2 ইঞ্চি গভীরে চাপ দিন, প্রতি মিনিটে 100-120 বার। জীবনাঙ্গ নিচে নেওয়ার অনুমতি দিন।",
     "tags": ["cpr", "cardiac", "resuscitation", "bengali"]},
    {"source": "translated_draft", "language": "bn", "type": "spinal_precautions",
     "text": "তাৎক্ষণিক বিপদ না হলে (আগুন, বন্যা, অজস্রতা) ব্যক্তিকে সরাবেন না। মাথা ও গলার কাছে হাত রাখুন। মেরুদণ্ড সরাসরি হাতে রাখুন। ব্যক্তির মাথা, গলা ও মেরুদণ্ড সবসময় একইরেখায় রাখুন।",
     "tags": ["spinal", "neck", "fracture", "immobilization", "bengali"]},
    {"source": "translated_draft", "language": "bn", "type": "shock_management",
     "text": "ব্যক্তিকে পিঠে হেলান দিয়ে মেঝেতে রাখুন। পা মেঝেতে ১২ ইঞ্চি (৩০ সেমি) উঁচু করুন। সংযতি আঘাত না হলে কোম্বল্টে রাখুন। উষ্ণ রাখতে চাদর বা জ্যাকেট দিন। কিছুই খাবেন বা পান করবেন না। শ্বাসপাল ও সচেতনতা পর্যবেক্ষণ করুন।",
     "tags": ["shock", "unconscious", "fainting", "bengali"]},
    {"source": "translated_draft", "language": "bn", "type": "recovery_position",
     "text": "ব্যক্তিকে পিঠে বাহিরে ঘোরান। মাথাটিকে পেছনে হেলে বাতাসের পথ খুলে রাখুন। উপরের পা হাঁটুতে বাঁধে দিয়ে স্থিতিশীল রাখুন। শ্বাস নিতে সক্ষম না হলে বাম দিকে ঘোরান।",
     "tags": ["recovery", "position", "airway", "bengali"]},
    {"source": "translated_draft", "language": "bn", "type": "fracture_management",
     "text": "হাড়কে আবার সোজা করতে চেষ্টা করবেন না। বোর্ড, কাগজ বা শক্তিশালী কার্ডবোর্ড দিয়ে আঘাতস্থলকে স্থির করুন। কাপড় দিয়ে ঘেরে দিন। পাতাটি আঘাতের উপর এবং নিচে বেঁধুন, সরাসরি উপরে নয়। প্রতি ১০ মিনিটে রক্তপ্রবাহ পরীক্ষা করুন।",
     "tags": ["fracture", "bone", "splint", "immobilization", "bengali"]},

    # Sinhala
    {"source": "translated_draft", "language": "si", "type": "bleeding_control",
     "text": "පිරිවර හෝ බැඳුමක් මගින් පිටුවට බලයක් දක්වන්න. අවම කාලයක් 10-15 විනාඩි බලය දරා තියිණුවන්න. ස්ථාවර පිටුවට ගැටෙන දේවල් ඉවත් නොකරන්න. කැපවීම ඉදිරියට ගියේ නම් තවත් පිරිවරක් තැටියට දක්වන්න. අන්තර්ජාල ගැටීමක් සඳහා 108 හෝ 112 වෙනුවට ඇමතින්න.",
     "tags": ["bleeding", "hemorrhage", "pressure", "first-aid", "sinhala"]},
    {"source": "translated_draft", "language": "si", "type": "cpr",
     "text": "පුද්ගලයෙකුට රඟපා තියෙන පොළේ පිටලකරන්න. එයාගේ පැත්තට අදින්න. අතකට සිටින අතට මිණියේ මධ්\u200dයයට අත පිටලකරන්න. දෙවන අත ඉහළට තබන්න සහ ඇඟිල් එකතු කරන්න. සැපතල සිටින ආයුබෝවය දිනා තබන්න.",
     "tags": ["cpr", "cardiac", "resuscitation", "sinhala"]},
    {"source": "translated_draft", "language": "si", "type": "spinal_precautions",
     "text": "අනතුරක් නොමැතිනම් පුද්ගලයෙකු ගෙන යන්න නොයුතු. පිරියක් සහ කතාව තබා ගන්න. සාරණය මේන්තුව තුළ පිරියක්, කතාව සහ පිහිටුම සඐඳුණු තරමට තියෙනු ලබන්න.",
     "tags": ["spinal", "neck", "fracture", "immobilization", "sinhala"]},
    {"source": "translated_draft", "language": "si", "type": "shock_management",
     "text": "පුද්ගලයෙකුට පසුපාදියේ මතකට හැර දමන්න. පා මේන්තුවක ඉහළට ඉදිරියට අවමක් 12 අඟ (30 සෑ.ම) ඉහළට ගන්න. තානාපති නොකරන අවස්ථාවක පිටියට ගැස්මක් ගොඩක් කරන්න. කිසියම් කාරණයක් කරන්න හෝ බොන්න නොකරන්න.",
     "tags": ["shock", "unconscious", "fainting", "sinhala"]},
    {"source": "translated_draft", "language": "si", "type": "recovery_position",
     "text": "පුද්ගලයෙකුට පසුපාදියේ පැත්තක පිහිටුවන්න. පිරියක් පිනා තබා වායු මාර්ගය විවෘත කරන්න. ඉහළ පා පැත්තක බැඳීමෙන් ස්ථාවරතාවක් තබා ගන්න.",
     "tags": ["recovery", "position", "airway", "sinhala"]},
    {"source": "translated_draft", "language": "si", "type": "fracture_management",
     "text": "ඉඳගැට නැවත පිහිටුවා ගැනීමට උත්සාහ නොකරන්න. පුහුණු පුටු, කඩේ හෝ බලෙක් පදනම් කරගෙන කැටයක් තුළත් කරන්න. විරම පාටමින් පුටුව තුළත් කරන්න. වඩාත් ඉහල සහ පහල කර නොබැඳන්න. ප්\u200dරතියකය පරීක්\u200dෂා කරන්න.",
     "tags": ["fracture", "bone", "splint", "immobilization", "sinhala"]},
]


async def seed_database():
    logger.info("Seeding database...")
    await init_db()

    async with async_session() as session:
        for svc in TN_HOSPITALS + TN_AMBULANCES + TN_POLICE + TN_BLOOD_BANKS:
            wkt = f"SRID=4326;POINT({svc['lng']} {svc['lat']})"
            await session.execute(
                text("""
                    INSERT INTO emergency_services
                        (name, service_type, trauma_grade, location, address, phone,
                         has_icu, has_ventilator, has_blood_bank, has_trauma_team,
                         capacity, verified)
                    VALUES
                        (:name, :type, :grade, ST_GeomFromText(:loc, 4326), :address, :phone,
                         :icu, :vent, :blood, :trauma,
                         :capacity, true)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "name": svc["name"],
                    "type": svc["type"],
                    "grade": svc.get("grade", 3),
                    "loc": wkt,
                    "address": svc.get("address", ""),
                    "phone": svc.get("phone", ""),
                    "icu": svc.get("icu", False),
                    "vent": svc.get("vent", False),
                    "blood": svc.get("blood", False),
                    "trauma": svc.get("trauma", False),
                    "capacity": json.dumps({"beds_total": svc.get("beds", 0)}),
                },
            )

        for proto in PROTOCOL_DATA:
            await session.execute(
                text("""
                    INSERT INTO protocol_chunks
                        (source, language, protocol_type, chunk_text, tags)
                    VALUES (:source, :language, :type, :text, :tags)
                """),
                {
                    "source": proto["source"],
                    "language": proto["language"],
                    "type": proto["type"],
                    "text": proto["text"],
                    "tags": proto["tags"],
                },
            )

        await session.commit()

    # Generate embeddings for protocol chunks
    embed_count = await generate_protocol_embeddings()

    count = len(TN_HOSPITALS) + len(TN_AMBULANCES) + len(TN_POLICE) + len(TN_BLOOD_BANKS)
    logger.info(f"Seed complete: {count} services + {len(PROTOCOL_DATA)} protocols + {embed_count} embeddings")


async def generate_protocol_embeddings() -> int:
    """Generate embeddings for protocol chunks that lack them, using sentence-transformers."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.warning("sentence-transformers not installed — skipping embedding generation")
        return 0

    model_name = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    try:
        model = SentenceTransformer(model_name)
    except Exception as e:
        logger.warning(f"Could not load embedding model '{model_name}': {e}")
        return 0

    from app.database import async_session as new_session
    from sqlalchemy import text as sql_text

    async with new_session() as session:
        result = await session.execute(
            sql_text("SELECT id, chunk_text FROM protocol_chunks WHERE embedding IS NULL")
        )
        rows = result.fetchall()
        if not rows:
            return 0

        ids = [row[0] for row in rows]
        texts = [row[1] for row in rows]
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

        for i, row_id in enumerate(ids):
            await session.execute(
                sql_text("UPDATE protocol_chunks SET embedding = :emb WHERE id = :id"),
                {"emb": json.dumps(embeddings[i].tolist()), "id": row_id},
            )
        await session.commit()
        return len(ids)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_database())