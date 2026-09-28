import datetime
import itertools
import os
import geonamescache
import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
import swisseph as swe
from timezonefinder import TimezoneFinder

# ==========================================
# 0. إعداد مسار ملفات الـ Ephemeris للكويكبات والكواكب
# ==========================================
EPHE_PATH = "./ephe"
if not os.path.exists(EPHE_PATH):
  os.makedirs(EPHE_PATH)

swe.set_ephe_path(EPHE_PATH)

# ==========================================
# 1. تهيئة قاعدة بيانات الدول والمدن العالمية
# ==========================================


@st.cache_data
def load_geo_data():
  gc = geonamescache.GeonamesCache()
  countries = gc.get_countries()
  cities = gc.get_cities()

  country_map = {c["name"]: code for code, c in countries.items()}
  sorted_countries = sorted(list(country_map.keys()))

  cities_by_country = {}
  for c_code in country_map.values():
    c_cities = [
        city for city in cities.values() if city["countrycode"] == c_code
    ]
    c_cities_sorted = sorted(
        c_cities, key=lambda x: x["population"], reverse=True
    )
    cities_by_country[c_code] = c_cities_sorted

  return gc, country_map, sorted_countries, cities_by_country


gc, country_map, country_list, cities_by_country = load_geo_data()


@st.cache_resource
def get_tz_finder():
  return TimezoneFinder()


tf = get_tz_finder()


def get_utc_julian_day(date_obj, time_obj, tz_str):
  local_tz = pytz.timezone(tz_str)
  dt = datetime.datetime.combine(date_obj, time_obj)
  local_dt = local_tz.localize(dt)
  utc_dt = local_dt.astimezone(pytz.utc)
  return swe.julday(
      utc_dt.year,
      utc_dt.month,
      utc_dt.day,
      utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0,
  )


def get_aspect(lon1, lon2, orb=8):
  diff = abs(lon1 - lon2)
  if diff > 180:
    diff = 360 - diff

  aspects = {
      "الاقتران": 0,
      "التسديس": 60,
      "التربيع": 90,
      "التثليث": 120,
      "المقابلة": 180,
  }

  for name, angle in aspects.items():
    if abs(diff - angle) <= orb:
      return name
  return None


# ==========================================
# 2. فئة التحليل الفلكي (AstroAnalyzer)
# ==========================================
class AstroAnalyzer:

  def __init__(self):
    self.planets = {
        "الشمس": "النشاط، الحيوية، الروح",
        "القمر": "العواطف، العائلة، المنزل",
        "عطارد": "الأخوة، المواصلات، الاتصالات",
        "الزهرة": "العلاقات الاجتماعية، الغرام، النعمة",
        "المريخ": "العمل، الحروب، الطاقة",
        "المشتري": "النمو، التوسع، الإزدهار",
        "زحل": "الرشود، المسؤولية، التراجع",
        "أورانوس": "عدم الإستقرار، الغير مألوف، الثورات",
        "نبتون": "ساتر الدخان، الضباب، اللصوص",
        "بلوتو": "التغير الجذري، العمق، المافيا",
    }

    self.signs = {
        "الحمل": "الطاقة، الحيوية، الإستقلال",
        "الثور": "الصلابة، الإستمرارية، الثبات",
        "الجوزاء": "الازدواجية، الفكر، التواصل",
        "السرطان": "الحساسية، الحماية، العائلة",
        "الأسد": "الفخامة، الإتقان، الملوك",
        "العذراء": "الفعالية، الإنتقاد، التحليل",
        "الميزان": "التوازن، العدالة، الدبلوماسية",
        "العقرب": "الأسرار، العمق، الشهوانية",
        "القوس": "النمو، التوسع، الإزدهار",
        "الجدي": "الإنضباط، السلطة، الجديّة",
        "الدلو": "اليوتوبيا، المثالية، الإبتكار",
        "الحوت": "الحساسية، البديهية، الروحانية",
    }

    self.houses = {
        "البيت الأول": "الطبع، المظهر، الصحة",
        "البيت الثاني": "المال، النقد، الممتلكات",
        "البيت الثالث": (
            "الأخوة، الجيران، الرحلات القصيرة، الفكر"
        ),
        "البيت الرابع": "العائلة، المنزل، الجزء الأخير من الحياة",
        "البيت الخامس": (
            "العلاقات الغرامية، الأولاد، الترفيه، الاستثمار"
        ),
        "البيت السادس": (
            "العمل اليومي، الصحة، أمراض قصيرة المدى، الحيوانات الأليفة"
        ),
        "البيت السابع": "الزواج، الشراكات، مشاكل قانونية",
        "البيت الثامن": (
            "موت الشخص، موت الأقارب والاصدقاء، الديون، الضرائب، العمليات الجراحية"
        ),
        "البيت التاسع": "السفر، الرحلات البعيدة، الدراسات العليا، المعتقد",
        "البيت العاشر": "المهنة، السمعة، الرتبة في المجتمع",
        "البيت الحادي عشر": "الأصدقاء، الداعمين، النوادي",
        "البيت الثاني عشر": (
            "الانعزال، المستشفيات، أمراض طويلة المدى، الروحانيات"
        ),
    }

    self.asteroids = {
        "كايرون": (
            "الجرح العميق الذي نحمله، وقدرتنا على التشافي وتقديم الحكمة"
            " الناتجة عن الألم للآخرين"
        ),
        "سيريس": (
            "مفهوم الرعاية والأمومة، كيفية تغذيتنا لأنفسنا وللآخرين، والإنتاجية"
        ),
        "بالاس": "الحكمة، الاستراتيجية، الذكاء الإبداعي، وإدراك الأنماط لتحقيق العدالة",
        "جونو": "الالتزام طويل الأمد، الزواج، الشراكات العميقة، ومفهوم الوفاء",
        "فيستا": (
            "التفاني، التركيز العميق، التضحية، والشعلة الروحية الداخلية للإنسان"
        ),
    }

    self.aspects = {
        "الاقتران": (
            "دمج الطاقات، تركيز شديد، قوة مكثفة قد تكون بناءة أو مربكة بناءً"
            " على طبيعة الكوكبين (0 درجة)"
        ),
        "التسديس": (
            "فرص داعمة، انسجام، تعاون، طاقة إيجابية تتطلب المبادرة لتفعيلها"
            " (60 درجة)"
        ),
        "التربيع": (
            "تحديات، توتر، صراع داخلي يحفز على اتخاذ قرارات قوية والتطور (90"
            " درجة)"
        ),
        "التثليث": (
            "انسجام تام، مواهب فطرية، تدفق سلس للطاقة، حظ ووفرة دون جهد كبير"
            " (120 درجة)"
        ),
        "المقابلة": (
            "مواجهة، شد وجذب، حاجة ملحة لإيجاد التوازن، الوعي والتعلم من خلال"
            " الآخرين (180 درجة)"
        ),
    }

  def analyze_placement(self, body, sign, house, is_asteroid=False):
    if is_asteroid:
      body_meaning = self.asteroids.get(body, "غير متوفر")
      body_type = "الكويكب"
    else:
      body_meaning = self.planets.get(body, "غير متوفر")
      body_type = "الكوكب"

    sign_meaning = self.signs.get(sign, "غير متوفر")
    house_meaning = self.houses.get(house, "غير متوفر")

    report = (
        f"<b>تحليل تواجد {body_type} ({body}) في برج ({sign}) وفي"
        f" ({house}):</b><br><br>"
        f"- <b>دلالة {body}:</b> يمثل ({body_meaning}).<br>"
        f"- <b>دلالة البرج:</b> يكتسب طابع ({sign_meaning}).<br>"
        f"- <b>دلالة البيت:</b> يتجلى هذا التأثير في مجالات"
        f" ({house_meaning}).<br><br>"
        f"💡 <b>الخلاصة:</b> تواجد {body} في {sign} بـ {house} يوجه طاقات"
        f" ({body_meaning.split('،')[0]}) بأسلوب يتسم بـ"
        f" ({sign_meaning.split('،')[0]})، وينعكس ذلك بشكل أساسي على حياة الفرد"
        f" من خلال ({house_meaning.split('،')[0]})."
    )
    return report

  def analyze_aspect(
      self,
      body1,
      body2,
      aspect_name,
      is_body1_asteroid=False,
      is_body2_asteroid=False,
  ):
    meaning1 = (
        self.asteroids.get(body1, "غير متوفر")
        if is_body1_asteroid
        else self.planets.get(body1, "غير متوفر")
    )
    meaning2 = (
        self.asteroids.get(body2, "غير متوفر")
        if is_body2_asteroid
        else self.planets.get(body2, "غير متوفر")
    )

    aspect_meaning = self.aspects.get(aspect_name, "غير متوفر")

    report = (
        f"<b>تحليل اتصال ({aspect_name}) بين ({body1}) و ({body2}):</b><br><br>"
        f"- <b>دلالة ({body1}):</b> يمثل ({meaning1}).<br>"
        f"- <b>دلالة ({body2}):</b> يمثل ({meaning2}).<br>"
        f"- <b>طبيعة الاتصال ({aspect_name}):</b> {aspect_meaning}.<br><br>"
        f"💡 <b>الخلاصة:</b> هذا الاتصال يخلق حالة من"
        f" ({aspect_meaning.split('،')[0]}) بين طاقة"
        f" ({meaning1.split('،')[0]}) الخاصة بـ {body1}، وطاقة"
        f" ({meaning2.split('،')[0]}) الخاصة بـ {body2}."
    )
    return report


# ==========================================
# 3. إعداد واجهة Streamlit والحسابات الفلكية
# ==========================================

st.set_page_config(page_title="تحليل الخارطة الميلادية الشاملة", layout="wide")
st.title("استخراج و تحليل الخارطة الميلادية والكويكبات (بدون ساعة الميلاد)")
st.write(
    "يعتمد هذا النظام على الخارطة الشمسية ونظام (كل برج بيت) مع حساب"
    " الاتصالات الفلكية والكويكبات - برمجة الفلكي و المبرمج الدكتور ملهم احمد - استرو رادار"
)
st.markdown("---")


BODIES = {
    "الشمس (Sun)": swe.SUN,
    "القمر (Moon)": swe.MOON,
    "عطارد (Mercury)": swe.MERCURY,
    "الزهرة (Venus)": swe.VENUS,
    "المريخ (Mars)": swe.MARS,
    "المشتري (Jupiter)": swe.JUPITER,
    "زحل (Saturn)": swe.SATURN,
    "أورانوس (Uranus)": swe.URANUS,
    "نبتون (Neptune)": swe.NEPTUNE,
    "بلوتو (Pluto)": swe.PLUTO,
    "راهو (North Node)": swe.TRUE_NODE,
    "ليليث (True Lilith)": swe.OSCU_APOG,
}

ASTEROIDS = {
    "كايرون (Chiron)": swe.CHIRON,
    "سيريس (Ceres)": swe.CERES,
    "بالاس (Pallas)": swe.PALLAS,
    "جونو (Juno)": swe.JUNO,
    "فيستا (Vesta)": swe.VESTA,
}

ZODIAC_SIGNS = [
    "الحمل",
    "الثور",
    "الجوزاء",
    "السرطان",
    "الأسد",
    "العذراء",
    "الميزان",
    "العقرب",
    "القوس",
    "الجدي",
    "الدلو",
    "الحوت",
]

HOUSE_ARABIC_NAMES = {
    1: "البيت الأول",
    2: "البيت الثاني",
    3: "البيت الثالث",
    4: "البيت الرابع",
    5: "البيت الخامس",
    6: "البيت السادس",
    7: "البيت السابع",
    8: "البيت الثامن",
    9: "البيت التاسع",
    10: "البيت العاشر",
    11: "البيت الحادي عشر",
    12: "البيت الثاني عشر",
}


def get_zodiac_sign_and_degree(longitude):
  sign_index = int(longitude // 30)
  degree = longitude % 30
  return ZODIAC_SIGNS[sign_index], sign_index, degree


with st.sidebar:
  st.header("بيانات الولادة والموقع")
  name = st.text_input("الاسم:", "مثال: أحمد")
  gender = st.selectbox("الجنس:", ["ذكر", "أنثى"])
  dob = st.date_input(
      "تاريخ الميلاد:",
      min_value=datetime.date(1900, 1, 1),
      max_value=datetime.date.today(),
  )

  selected_country = st.selectbox("الدولة:", country_list)
  country_code = country_map[selected_country]

  country_cities_data = cities_by_country.get(country_code, [])
  city_names = [city["name"] for city in country_cities_data]

  if not city_names:
    city_names = ["لا توجد بيانات مدن لهذه الدولة"]

  selected_city_name = st.selectbox("المدينة:", city_names)

  submit = st.button("استخراج وتحليل الخارطة")

if (
    submit
    and name
    and dob
    and selected_city_name != "لا توجد بيانات مدن لهذه الدولة"
):
  city_data = next(
      (city for city in country_cities_data if city["name"] == selected_city_name),
      None,
  )

  if city_data:
    lat = city_data["latitude"]
    lng = city_data["longitude"]

    tz_str = tf.timezone_at(lng=lng, lat=lat)
    if not tz_str:
      tz_str = "UTC"

    default_time = datetime.time(12, 0)
    jd = get_utc_julian_day(dob, default_time, tz_str)

    results = []
    sun_sign_index = 0

    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    for name_ar, planet_id in BODIES.items():
      try:
        pos, ret = swe.calc_ut(jd, planet_id, flags)
        longitude = pos[0]
        sign_name, sign_idx, degree = get_zodiac_sign_and_degree(longitude)

        if planet_id == swe.SUN:
          sun_sign_index = sign_idx

        results.append({
            "الكوكب": name_ar,
            "البرج": sign_name,
            "الدرجة": f"{degree:.2f}°",
            "خط الطول": longitude,
        })
      except Exception as e:
        st.error(f"خطأ في حساب {name_ar}: {e}")

    try:
      rahu_lon = next(
          r["خط الطول"]
          for r in results
          if r["الكوكب"] == "راهو (North Node)"
      )
      ketu_lon = (rahu_lon + 180) % 360
      ketu_sign, _, ketu_deg = get_zodiac_sign_and_degree(ketu_lon)
      results.append({
          "الكوكب": "كيتو (South Node)",
          "البرج": ketu_sign,
          "الدرجة": f"{ketu_deg:.2f}°",
          "خط الطول": ketu_lon,
      })
    except StopIteration:
      pass

    for name_ar, ast_id in ASTEROIDS.items():
      try:
        pos, ret = swe.calc_ut(jd, ast_id, flags)
        longitude = pos[0]
        sign_name, _, degree = get_zodiac_sign_and_degree(longitude)
        results.append({
            "الكوكب": name_ar,
            "البرج": sign_name,
            "الدرجة": f"{degree:.2f}°",
            "خط الطول": longitude,
        })
      except Exception:
        pass

    for r in results:
      planet_sign_index = (
          ZODIAC_SIGNS.index(r["البرج"]) if r["البرج"] in ZODIAC_SIGNS else -1
      )
      if planet_sign_index != -1:
        house_number = ((planet_sign_index - sun_sign_index) % 12) + 1
        r["البيت"] = HOUSE_ARABIC_NAMES.get(house_number, "-")
      else:
        r["البيت"] = "-"

    aspects_results = []
    for body1, body2 in itertools.combinations(results, 2):
      lon1 = body1["خط الطول"]
      lon2 = body2["خط الطول"]
      aspect = get_aspect(lon1, lon2, orb=8)

      if aspect:
        aspects_results.append({
            "الجرم الأول": body1["الكوكب"],
            "الجرم الثاني": body2["الكوكب"],
            "الاتصال": aspect,
        })

    display_results = [
        {k: v for k, v in r.items() if k != "خط الطول"} for r in results
    ]

    st.success(
        f"تم حساب مواقع الكواكب بنجاح لـ: {name} ({gender}) -"
        f" {selected_country}، {selected_city_name}"
    )
    st.info(
        f"💡 تم اعتبار برج **{ZODIAC_SIGNS[sun_sign_index]}** (برج الشمس) كبيت"
        f" أول في الخارطة. تم الحساب بناءً على الساعة 12:00 ظهراً بالتوقيت"
        f" المحلي لمدينة {selected_city_name}."
    )

    st.subheader("مواقع الكواكب والكويكبات والبيوت")
    df_planets = pd.DataFrame(display_results)
    st.dataframe(df_planets, width="stretch")

    if aspects_results:
      st.subheader("الاتصالات الفلكية (Aspects)")
      df_aspects = pd.DataFrame(aspects_results)
      st.dataframe(df_aspects, width="stretch")

    st.header("🔮 التقرير الفلكي الشامل")
    analyzer = AstroAnalyzer()

    st.subheader("أولاً: تحليل التواجدات (الكواكب والكويكبات في الأبراج والبيوت)")
    for r in results:
      full_name = r["الكوكب"]
      sign = r["البرج"]
      house = r["البيت"]

      body_ar = full_name.split(" (")[0]
      is_asteroid = body_ar in analyzer.asteroids

      if (body_ar in analyzer.planets or is_asteroid) and house != "-":
        with st.expander(f"تحليل تواجد {body_ar} في برج {sign} ({house})"):
          report = analyzer.analyze_placement(
              body=body_ar, sign=sign, house=house, is_asteroid=is_asteroid
          )
          st.markdown(report, unsafe_allow_html=True)

    st.subheader("ثانياً: تحليل الاتصالات الفلكية")
    if aspects_results:
      for asp in aspects_results:
        body1_full = asp["الجرم الأول"]
        body2_full = asp["الجرم الثاني"]
        aspect_name = asp["الاتصال"]

        body1_ar = body1_full.split(" (")[0]
        body2_ar = body2_full.split(" (")[0]

        is_ast1 = body1_ar in analyzer.asteroids
        is_ast2 = body2_ar in analyzer.asteroids

        if (body1_ar in analyzer.planets or is_ast1) and (
            body2_ar in analyzer.planets or is_ast2
        ):
          with st.expander(f"اتصال {aspect_name} بين {body1_ar} و {body2_ar}"):
            report_asp = analyzer.analyze_aspect(
                body1=body1_ar,
                body2=body2_ar,
                aspect_name=aspect_name,
                is_body1_asteroid=is_ast1,
                is_body2_asteroid=is_ast2,
            )
            st.markdown(report_asp, unsafe_allow_html=True)
    else:
      st.write(
          "لا توجد اتصالات فلكية رئيسية في هذه الخارطة ضمن المسافة المسموحة."
      )

    # --- تجهيز محتوى الـ HTML الشامل (الجدول + التواجدات + الاتصالات) ---
    placements_html_report = ""
    for r in results:
      full_name = r["الكوكب"]
      sign = r["البرج"]
      house = r["البيت"]
      body_ar = full_name.split(" (")[0]
      is_asteroid = body_ar in analyzer.asteroids
      if (body_ar in analyzer.planets or is_asteroid) and house != "-":
        rep = analyzer.analyze_placement(
            body=body_ar, sign=sign, house=house, is_asteroid=is_asteroid
        )
        placements_html_report += f"""
            <div class="analysis-card">
                <h3>تحليل تواجد {body_ar} في برج {sign} ({house})</h3>
                <p>{rep}</p>
            </div>
            """

    aspects_html_report = ""
    if aspects_results:
      for asp in aspects_results:
        body1_full = asp["الجرم الأول"]
        body2_full = asp["الجرم الثاني"]
        aspect_name = asp["الاتصال"]
        body1_ar = body1_full.split(" (")[0]
        body2_ar = body2_full.split(" (")[0]
        is_ast1 = body1_ar in analyzer.asteroids
        is_ast2 = body2_ar in analyzer.asteroids
        if (body1_ar in analyzer.planets or is_ast1) and (
            body2_ar in analyzer.planets or is_ast2
        ):
          rep_asp = analyzer.analyze_aspect(
              body1=body1_ar,
              body2=body2_ar,
              aspect_name=aspect_name,
              is_body1_asteroid=is_ast1,
              is_body2_asteroid=is_ast2,
          )
          aspects_html_report += f"""
              <div class="analysis-card">
                  <h3>اتصال {aspect_name} بين {body1_ar} و {body2_ar}</h3>
                  <p>{rep_asp}</p>
              </div>
              """
    else:
      aspects_html_report = (
          "<p>لا توجد اتصالات فلكية رئيسية في هذه الخارطة ضمن المسافة"
          " المسموحة.</p>"
      )

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تقرير التحليل الفلكي الشامل - {name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #ffffff;
            color: #333;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .report-container {{
            max-width: 900px;
            margin: auto;
            background: #ffffff;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            margin-bottom: 5px;
            font-size: 24px;
        }}
        .subtitle {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 25px;
            font-size: 14px;
        }}
        h2 {{
            color: #2980b9;
            border-bottom: 2px solid #2980b9;
            padding-bottom: 5px;
            margin-top: 30px;
            font-size: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            margin-bottom: 25px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: center;
            border-bottom: 1px solid #e2e8f0;
            font-size: 14px;
        }}
        th {{
            background-color: #2980b9;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f1f5f9;
        }}
        .analysis-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-right: 4px solid #2980b9;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .analysis-card h3 {{
            margin-top: 0;
            color: #1e293b;
            font-size: 16px;
        }}
        .footer {{
            margin-top: 35px;
            text-align: center;
            font-size: 12px;
            color: #95a5a6;
            border-top: 1px solid #e2e8f0;
            padding-top: 15px;
        }}
        .print-btn {{
            display: block;
            width: 220px;
            margin: 30px auto;
            padding: 12px;
            background-color: #27ae60;
            color: white;
            text-align: center;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }}
        .print-btn:hover {{
            background-color: #219653;
        }}
        @media print {{
            .print-btn {{ display: none; }}
            body {{ padding: 0; }}
            .analysis-card {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <h1>تقرير التحليل الفلكي الشامل: {name}</h1>
        <div class="subtitle">تاريخ الميلاد: {dob} | المدينة: {selected_city_name} ({selected_country}) | الجنس: {gender}</div>
        
        <h2>جدول مواقع الكواكب والكويكبات والبيوت</h2>
        <table>
            <thead>
                <tr>
                    <th>الجرم السماوي / الكويكب</th>
                    <th>البرج</th>
                    <th>الدرجة</th>
                    <th>البيت المقابل</th>
                </tr>
            </thead>
            <tbody>
"""
    for item in display_results:
      html_content += f"""
                <tr>
                    <td><b>{item['الكوكب']}</b></td>
                    <td>{item['البرج']}</td>
                    <td>{item['الدرجة']}</td>
                    <td>{item['البيت']}</td>
                </tr>
"""
    html_content += f"""
            </tbody>
        </table>

        <h2>أولاً: تحليل التواجدات (الكواكب والكويكبات في الأبراج والبيوت)</h2>
        {placements_html_report}

        <h2>ثانياً: تحليل الاتصالات الفلكية (Aspects)</h2>
        {aspects_html_report}

        <button class="print-btn" onclick="window.print()">🖨️ طباعة التقرير الشامل / حفظ PDF</button>

        <div class="footer">
            تم استخراج هذا التقرير الشامل وإعداد الحسابات آلياً عبر نظام Swiss Ephemeris وتطبيق التحليل الفلكي.
        </div>
    </div>
</body>
</html>
"""

    # معاينة وعرض التقرير الشامل مباشرة داخل التطبيق
    st.markdown("---")
    st.subheader("📄 معاينة تقرير الطباعة الشامل الجاهز")
    components.html(html_content, height=750, scrolling=True)

    # زر التحميل المباشر لملف HTML
    output_filename = "comprehensive_astro_report.html"
    with open(output_filename, "w", encoding="utf-8") as f:
      f.write(html_content)

    with open(output_filename, "rb") as file:
      st.download_button(
          label="📥 تحميل التقرير الشامل كملف HTML",
          data=file,
          file_name=output_filename,
          mime="text/html",
      )

  else:
    st.error("حدث خطأ في جلب بيانات المدينة المحددة.")