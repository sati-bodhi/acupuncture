from django.shortcuts import render
from acupuncture.lookup import *
from acupuncture.element import *
from datetime import datetime
import pytz
import geocoder
import ephem
from acupuncture.diagnostics import solartime_by_ip, solartime_by_city, horary_calc
import jieba
import re
import hanlp
from hanlp.components.tokenizers.transformer import TransformerTaggingTokenizer

# Tokenizer
tok = update_tokenizer_wordlist()

# Create your views here.


def homepage(request):
    return render(request, template_name='data_assist/index.html')


def query(request):
    """Database query."""
    search_term = request.GET.get('q')
    search_cat = request.GET.get('category')
    acupoint = []
    meridian = []
    pentashu = None

    if search_term:
        if search_cat == "acupoint":
            acupoint = get_acupoint(search_term)
        elif search_cat == "meridian":
            meridian = get_meridian(search_term)

    elif request.method == "POST":
        search_cat = request.POST.get('category')
        search_term = request.POST.get('q')

        if search_cat == "acupoint":
            acupoint = get_acupoint(search_term)
        elif search_cat == "meridian":
            meridian = get_meridian(search_term)

    else:
        return render(request, template_name='data_assist/query.html')

    if acupoint:

        if len(acupoint) > 1:
            multiple = True
            acupoint = [acupoint[i:i+4] for i in range(0, len(acupoint), 4)]
            return render(request, template_name='data_assist/query.html',
                          context={
                              "multiple": multiple,
                              "acupoint": acupoint,
                          })
        else:
            acu_id, zh, tr, en, meridian_id = acupoint[0]
            meridian = get_meridian(meridian_id)
            pentashu = get_pentashu_label(acu_id)
            mu_shu = get_mu_shu_label(acu_id)
            found = True
            loc = get_location(acu_id)  # string describing location of acupoint
            loc = add_href(loc)

            return render(request, template_name='data_assist/query.html',
                          context={
                              "acupoint": True,
                              "found": found,
                              "id": acu_id,
                              "zh_name": zh,
                              "tr_name": tr,
                              "en_name": en,
                              "located": loc,
                              "meridian_id": meridian[0][0],
                              "meridian": meridian[0][1],
                              "pentashu": pentashu,
                              "mushu": mu_shu,
                          })

    elif meridian:

        if len(meridian) > 1:
            multiple = True
            return render(request, template_name='data_assist/query.html',
                          context={
                              "multiple": multiple,
                              "meridian": meridian,
                          })
        else:
            meridian_id, zh, tr, en, abbrev, extra = meridian[0]
            route, route_src = get_route(meridian_id)
            route = add_href(route)
            route = markup_commentary(route)
            points = acupoints_in_meridian(meridian_id)
            pentashu, pentashu_labels = in_pentashu(points)
            mu_shu, mu_shu_labels = in_mu_shu(points)
            table_data = zip(points, pentashu_labels, mu_shu_labels)

            if extra == 1:
                extra = True
            else:
                extra = False

            if meridian_id in ["CV", "GV"]:
                cgv = True
            else:
                cgv = False

            return render(request, template_name='data_assist/query.html',
                          context={
                              "meridian": True,
                              "meridian_found": True,
                              "mu_shu": mu_shu,
                              "pentashu": pentashu,
                              "extra": extra,
                              "ren_du": cgv,
                              "meridian_id": meridian_id,
                              "zh_meridianname": zh,
                              "tr_meridianname": tr,
                              "en_meridianname": en,
                              "abbrev_meridianname": abbrev,
                              "route": route,
                              "route_src": route_src,
                              "table_data": table_data,
                          })

    else:
        not_found = True
        return render(request, template_name='data_assist/query.html',
                      context={
                          "not_found": not_found,
                          "keyword": search_term,
                      })


def in_pentashu(points):
    pentashu_label = [get_pentashu_label(point[0]) for point in points]
    if any(pentashu_label):
        pentashu = True
    else:
        pentashu = False

    return pentashu, pentashu_label


def in_mu_shu(points):
    mu_shu_label = [get_mu_shu_label(point[0]) for point in points]
    if any(mu_shu_label):
        mu_shu = True
    else:
        mu_shu = False

    return mu_shu, mu_shu_label


def markup_commentary(string):
    string = re.sub("{{", "<small style='color:#996666'> ", string)
    string = re.sub("}}", " </small>", string)
    return string


def add_href(string, category="acupoint"):
    """Add hyperlink to keywords on database."""
    wordlist = href_search(string)
    # wordlist = set(match[0] for match in href_matches)

    for acu_id, word in wordlist:
        string = string.replace(word,
                          '<a href="/query?q=' + acu_id + '&category=' + category + '">' + word + '</a>')

    return string


def href_search(string):
    hits = []
    i = 0
    string_iter=iter(string)
    seg_list = tok(string)

    def narrow_down_on(target):
        if len(target) == 1:
            acu_id = target[0][0]
            hits.append((acu_id, word))
            return
        elif hits:
            ref = hits[-1][0]  # Use previous hit as reference
            diff = None
            for i, candidate in enumerate(target):
                sno_candidate = int(re.sub("[A-Z]+", "", candidate[0]))
                sno_ref = int(re.sub("[A-Z]+", "", ref))
                meridian = candidate[4]
                if meridian in ref:
                    diff_prev = diff
                    diff = abs(sno_ref - sno_candidate)
                    if diff_prev is not None:
                        if diff <= diff_prev:
                            target = [candidate]
                            narrow_down_on(target)
                        else:
                            target = [target[i-1]]
                            narrow_down_on(target)

    for word in seg_list:
        target = get_acupoint(word, fuzzy=False)
        if target:
            narrow_down_on(target)

    hits = set(hits)

    return hits


def render_prescription(prescription):
    """Render parsed prescription as hyperlinked html text."""
    rendered = [f"""{action}<a href='/query?q={point_id}&category=acupoint'>{point}</a>"""
                for point_id, point, action in prescription]

    return rendered


def diagnose(request):
    return render(request, template_name='data_assist/diagnose_menu.html')


def eight_principles(request):
    """Basic yinyang and blood-energy levels. 氣血陰陽"""

    renying = request.GET.get('renying')
    pulse = request.GET.get('pulse')
    pulse_yinyang = request.GET.get('pulse-yinyang')

    if renying:
        result = True
        meridian_rel_yinyang_lvl = False  # meridian relative yinyang level
        qty_prescription = []
        qual_prescription = []
        meridian_prescription = []

        diagnosis, treat_qty, treat_qual = qixue_yinyang(renying, pulse)

        points = parse_prescription(treat_qty)
        qty_prescription += render_prescription(points)

        points = parse_prescription(treat_qual)
        qual_prescription += render_prescription(points)

        if pulse_yinyang:

            meridian_rel_yinyang_lvl = True  # meridian relative yinyang level
            prescription_list = meridian_yinyang(pulse_yinyang)

            points = parse_prescription(prescription_list)
            meridian_prescription += render_prescription(points)

        return render(request, template_name='data_assist/eight_principles.html',
                      context={
                                "result": result,
                                "rel_yinyang": meridian_rel_yinyang_lvl,
                                "diagnosis": diagnosis,
                                "treat_qty": qty_prescription,
                                "treat_qual": qual_prescription,
                                "treat_meridian": meridian_prescription,
                                })

    else:
        return render(request, template_name='data_assist/eight_principles.html')


def channels(request):
    # 十二正經
    prevent = request.GET.getlist('prevent')
    treat = request.GET.getlist('treat')
    method = request.GET.get('method')
    knot = request.GET.getlist('knot')

    preventive = False
    expulsive = False
    connect = False
    preventive_presp = []  # prescriptions list
    treatment_presp = []
    knot_presp = []

    if prevent:
        preventive = True
        preventive_points = []
        for item in prevent:
            pathogen = get_pathogen(item)
            if method == "mother_son":
                preventive_points.append(phenom_preventive(pathogen))
            elif method == "elem":
                preventive_points.append(phenom_preventive(pathogen, method="elem"))

        for i, prescription in enumerate(preventive_points):
            pathogen_label = "防" + get_pathogen(prevent[i])
            points = parse_prescription(prescription)
            preventive_presp.append((pathogen_label, render_prescription(points)))

    if treat:
        expulsive = True
        treatment_points = []
        for item in treat:
            pathogen = get_pathogen(item)
            treatment_points.append(phenom_treatment(pathogen))

        for i, prescription in enumerate(treatment_points):
            pathogen_label = "袪" + get_pathogen(treat[i])
            points = parse_prescription(prescription)
            treatment_presp.append((pathogen_label, render_prescription(points)))

    if knot:
        connect = True
        knot_points = []
        for meridian in knot:
            knot_points.append(get_root_knot(meridian))

        for zh, tr, prescription in knot_points:
            knot_label = "連接" + zh + "經"
            points = parse_prescription([prescription])
            knot_presp.append((knot_label, render_prescription(points)))

    if all([not treat, not prevent, not knot]):
        return render(request, template_name='data_assist/channels.html')
    else:
        return render(request, template_name='data_assist/channels.html',
                      context = {
                          "result": True,
                          "prevent": preventive,
                          "treat": expulsive,
                          "knot": connect,
                          "prescription_preventive": preventive_presp,
                          "prescription_treatment": treatment_presp,
                          "prescription_knot": knot_presp,
                      })


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def horary(request):
    cities = ['Abu Dhabi', 'Adelaide', 'Almaty', 'Amsterdam', 'Antwerp', 'Arhus', 'Athens', 'Atlanta', 'Auckland',
               'Baltimore', 'Bangalore', 'Bangkok', 'Barcelona', 'Beijing', 'Berlin', 'Birmingham', 'Bogota', 'Bologna',
               'Boston', 'Bratislava', 'Brazilia', 'Brisbane', 'Brussels', 'Bucharest', 'Budapest', 'Buenos Aires',
               'Cairo', 'Calgary', 'Cape Town', 'Caracas', 'Chicago', 'Cleveland', 'Cologne', 'Colombo', 'Columbus',
               'Copenhagen', 'Dallas', 'Detroit', 'Dresden', 'Dubai', 'Dublin', 'Dusseldorf', 'Edinburgh', 'Frankfurt',
               'Geneva', 'Genoa', 'Glasgow', 'Gothenburg', 'Guangzhou', 'Hamburg', 'Hanoi', 'Helsinki',
               'Ho Chi Minh City', 'Hong Kong', 'Houston', 'Istanbul', 'Jakarta', 'Johannesburg', 'Kansas City', 'Kiev',
               'Kuala Lumpur', 'Leeds', 'Lille', 'Lima', 'Lisbon', 'London', 'Los Angeles', 'Luxembourg', 'Lyon',
               'Madrid', 'Manchester', 'Manila', 'Marseille', 'Melbourne', 'Mexico City', 'Miami', 'Milan',
               'Minneapolis', 'Montevideo', 'Montreal', 'Moscow', 'Mumbai', 'Munich', 'New Delhi', 'New York', 'Osaka',
               'Oslo', 'Paris', 'Philadelphia', 'Prague', 'Richmond', 'Rio de Janeiro', 'Riyadh', 'Rome', 'Rotterdam',
               'San Francisco', 'Santiago', 'Sao Paulo', 'Seattle', 'Seoul', 'Shanghai', 'Singapore', 'St. Petersburg',
               'Stockholm', 'Stuttgart', 'Sydney', 'Taipei', 'Tashkent', 'Tehran', 'Tel Aviv', 'The Hague', 'Tijuana',
               'Tokyo', 'Toronto', 'Turin', 'Utrecht', 'Vancouver', 'Vienna', 'Warsaw', 'Washington', 'Wellington',
               'Zurich']
    cities_zh = ['阿布扎比', '阿德萊德', '阿拉木圖', '阿姆斯特丹', '安特衛普', '阿爾胡斯', '雅典', '亞特蘭大', '奧克蘭', '巴爾的摩', '班加羅爾', '曼谷', '巴塞羅那',
                  '北京', '柏林', '伯明翰', '波哥大', '博洛尼亞', '波士頓', '布拉迪斯拉發', '巴西', '布里斯班', '布魯塞爾', '布加勒斯特', '布達佩斯', '布宜諾斯艾利斯',
                  '開羅', '卡爾加里', '開普敦', '加拉加斯', '芝加哥', '克利夫蘭', '科隆', '科倫坡', '哥倫布', '哥本哈根', '達拉斯', '底特律', '德累斯頓', '迪拜',
                  '都柏林', '杜塞爾多夫', '愛丁堡', '法蘭克福', '日內瓦', '熱那亞', '格拉斯哥', '哥德堡', '廣州', '漢堡', '河內', '赫爾辛基', '胡志明市', '香港',
                  '休斯頓', '伊斯坦布爾', '雅加達', '約翰內斯堡', '堪薩斯城', '基輔', '吉隆坡', '利茲', '里爾', '利馬', '里斯本', '倫敦', '洛杉磯', '盧森堡',
                  '里昂', '馬德里', '曼徹斯特', '馬尼拉', '馬賽', '墨爾本', '墨西哥城', '邁阿密', '米蘭', '明尼阿波利斯', '蒙得維的亞', '蒙特利爾', '莫斯科', '孟買',
                  '慕尼黑', '新德里', '紐約', '大阪', '奧斯陸', '巴黎', '費城', '布拉格', '里士滿', '里約熱內盧', '利雅得', '羅馬', '鹿特丹', '舊金山', '聖地亞哥',
                  '聖保羅', '西雅圖', '首爾', '上海', '新加坡', '聖彼得堡', '斯德哥爾摩', '斯圖加特', '悉尼', '台北', '塔什幹', '德黑蘭', '特拉維夫', '海牙',
                  '蒂華納', '東京', '多倫多', '都靈', '烏得勒支', '溫哥華', '維也納', '華沙', '華盛頓', '惠靈頓', '蘇黎世']

    cities_zh = zip(cities, cities_zh)

    solartime, timezone = solartime_by_ip()

    timezone = pytz.timezone(timezone)
    dt_aware = datetime.now(timezone)

    curr_loc_hr = solartime.datetime().strftime("%H")
    hr_name, hr_meridian_id, hr_meridian = get_horary(curr_loc_hr)

    city = request.GET.get('city')

    if request.method == "GET" and city is not None:

        depart_solar, depart_tz = solartime_by_city(city)

        depart_tz = pytz.timezone(depart_tz)
        dt_depart = datetime.now(depart_tz)

        depart_hr = depart_solar.datetime().strftime("%H")
        depart_hr_name, depart_hr_meridian_id, depart_hr_meridian = get_horary(depart_hr)

        prescription = horary_calc(depart_hr_meridian_id, hr_meridian_id)

        luo_rendered = None
        transfer_rendered = None
        luo_desc = None
        transfer_desc = None
        result = None

        if prescription:
            result = True
            if prescription[0]:
                # 子午線(絡脈)
                luo = prescription[1][0]
                luo = parse_prescription(luo)
                luo_rendered = render_prescription(luo)

                luo_desc = prescription[1][1]

                if prescription[2]:
                    transfer = prescription[2][0]
                    transfer = [parse_prescription(pair) for pair in transfer]
                    transfer_rendered = [render_prescription(presc) for presc in transfer]

                    transfer_desc = prescription[2][1]
            else:
                transfer = prescription[1][0]
                transfer = [parse_prescription(pair) for pair in transfer]
                transfer_rendered = [render_prescription(presc) for presc in transfer]

                transfer_desc = prescription[1][1]

        if is_ajax(request):
            return render(request, template_name='data_assist/include/jetlag_form_result.html',
                          context={
                              "result": result,
                              "depart": True,
                              "depart_time": dt_depart.strftime("%x  %X"),
                              "depart_timezone": depart_tz,
                              "depart_solar_time": str(depart_solar),
                              "depart_hour": depart_hr_name,
                              "depart_meridian": depart_hr_meridian,
                              "cities": cities,
                              "cities_zh": cities_zh,
                              "luo": luo_rendered,
                              "luo_desc": luo_desc,
                              "transfer": list(zip(transfer_desc, transfer_rendered)),
                          })

        else:
            return render(request, template_name='data_assist/horary.html',
                          context={
                              "result": result,
                              "local_time": dt_aware.strftime("%x  %X"),
                              "local_timezone": timezone,
                              "local_solar_time": str(solartime),
                              "local_hour": hr_name,
                              "local_meridian": hr_meridian,
                              "depart": True,
                              "depart_time": dt_depart.strftime("%x  %X"),
                              "depart_timezone": depart_tz,
                              "depart_solar_time": str(depart_solar),
                              "depart_hour": depart_hr_name,
                              "depart_meridian": depart_hr_meridian,
                              "cities": cities,
                              "cities_zh": cities_zh,
                              "luo": luo_rendered,
                              "luo_desc": luo_desc,
                              "transfer": list(zip(transfer_desc, transfer_rendered)),
                          })

    else:
        return render(request, template_name='data_assist/horary.html',
                      context={
                          "local_time": dt_aware.strftime("%x  %X"),
                          "local_timezone": timezone,
                          "local_solar_time": str(solartime),
                          "local_hour": hr_name,
                          "local_meridian": hr_meridian,
                          "cities": cities,
                          "cities_zh": cities_zh,
                      })


def elements(request):
    # 五行
    organ_energy = request.GET.get("organEnergy")
    mother_overload = request.GET.get("motherOverload")

    sp_energy = request.GET.get("spEnergy")
    sp_mother_overload = request.GET.get("spMotherOverload")

    s = Season()
    this_season = s.current_season()
    lord_id = s.seasonal_lord(this_season[0])

    earth_energy = s.earth_energy_timeframe(this_season[1])

    a = Acute()
    mother, son, minister, inhibited = ["－".join(a.organ_viscera_zh(i)) for i in a.relative_states(lord_id)]
    lord = "－".join(a.organ_viscera_zh(lord_id))

    earth_mother, earth_son, earth_minister, earth_inhibited = \
        ["－".join(a.organ_viscera_zh(i)) for i in a.relative_states("SP")]
    earth_lord = "－".join(a.organ_viscera_zh("SP"))

    G, graph = a.graph()

    if sp_energy == "-" and sp_mother_overload:
        prescribe = a.diagnose("SP", sp_energy, mother_overload=True)
    elif sp_energy:
        prescribe = a.diagnose("SP", sp_energy)
    else:
        if organ_energy == "-" and mother_overload:
            prescribe = a.diagnose(lord_id, organ_energy, mother_overload=True)
        else:
            prescribe = a.diagnose(lord_id, organ_energy)

    p = Pentashu()
    attrib = [p.get_attributes(a) for a, t in prescribe]

    treatment = parse_prescription(prescribe)
    treatment = render_prescription(treatment)
    treatment = zip(treatment, attrib)

    if organ_energy is None and sp_energy is None:
        return render(request, template_name='data_assist/elements.html',
                      context={
                          "season": this_season,
                          "lord_id": lord_id,
                          "lord": lord,
                          "mother": mother,
                          "son": son,
                          "minister": minister,
                          "inhibited": inhibited,
                          "earth_energy": earth_energy,
                          "E_lord": earth_lord,
                          "E_mother": earth_mother,
                          "E_son": earth_son,
                          "E_minister": earth_minister,
                          "E_inhibited": earth_inhibited,
                          "graph": graph,
                      })
    else:
        return render(request, template_name='data_assist/elements.html',
                      context={
                          "season": this_season,
                          "lord_id": lord_id,
                          "lord": lord,
                          "mother": mother,
                          "son": son,
                          "minister": minister,
                          "inhibited": inhibited,
                          "earth_energy": earth_energy,
                          "E_lord": earth_lord,
                          "E_mother": earth_mother,
                          "E_son": earth_son,
                          "E_minister": earth_minister,
                          "E_inhibited": earth_inhibited,
                          "graph": graph,
                          "prescription": treatment,
                          "result": True,
                      })


def mushu(request):
    # 募俞穴
    som_emo = request.POST.get("som_emo")
    jb_func = request.POST.get("jb_func")

    if som_emo and jb_func:
        return render(request, template_name='data_assist/mushu.html',
                      context={
                          "category_elected": True,
                          "som_emo": som_emo,
                          "jb_func": jb_func,
                      })
    else:
        return render(request, template_name='data_assist/mushu.html')


def extraordinary(request):
    return render(request, template_name='data_assist/extraordinary.html')


def jingjin(request):
    # 經筋
    return render(request, template_name='data_assist/jingjin.html')


def jingbie(request):
    # 經別
    return render(request, template_name='data_assist/jingbie.html')


def luo(request):
    return render(request, template_name='data_assist/luo.html')


def group_luo(request):
    return render(request, template_name='data_assist/group_luo.html')


if __name__ == '__main__':
    pass
