from django.shortcuts import render
from acupuncture.lookup import *
from acupuncture.element import *
from acupuncture.extraordinary import *
from acupuncture.complement import *
from acupuncture.meridian import Phenomena
from datetime import datetime
import pytz
from acupuncture.diagnostics import solartime_by_ip, solartime_by_city, horary_calc
import re

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
    meridian_treatment_label = None

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
            acupoint = [acupoint[i:i + 4] for i in range(0, len(acupoint), 4)]
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
            extra = get_extra_id(acu_id)

            ex = Extraordinary()
            master_id = ex.is_master_point(acu_id)
            master = id_to_meridian_name(master_id, abbrev=True) if master_id else None
            master = (master_id, master) if master_id else None

            tonify_meridian = get_meridian_treatment_pt(acu_id, "++")
            disperse_meridian = get_meridian_treatment_pt(acu_id, "--")
            if tonify_meridian:
                meridian_treatment_label = tonify_meridian + "補穴"
            elif disperse_meridian:
                meridian_treatment_label = disperse_meridian + "瀉穴"
            entry_exit = get_entry_exit_pt(acu_id)

            luo = Luo()
            luo = luo.is_luo_point(acu_id)

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
                              "extra": extra,
                              "master": master,
                              "luo": luo,
                              "treat_meridian": meridian_treatment_label,
                              "entry_exit": entry_exit,
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
    wordlist, cum_chars = href_search(string)
    # wordlist = set(match[0] for match in href_matches)

    segmented_str = []
    for char in cum_chars:
        segmented_str.append(string[:char])
        string = string[char:]

    segmented_str.append(string)

    href_str = []
    for i, point in enumerate(wordlist):
        acu_id, word = point
        href_str.append(segmented_str[i].replace(word,
                                                 '<a href="/query?q=' + acu_id + '&category=' + category + '">' + word + '</a>'))

    if len(href_str) < len(segmented_str):
        href_str.append(segmented_str[-1])

    string = "".join(href_str)

    return string


def href_search(string):
    hits = []
    i = 0
    string_iter = iter(string)
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
                            target = [target[i - 1]]
                            narrow_down_on(target)

    chars = 0
    cumulated_chars = []
    for word in seg_list:
        target = get_acupoint(word, fuzzy=False)
        chars += len(word)
        if target:
            narrow_down_on(target)
            cumulated_chars.append(chars)
            chars = 0

    # hits = set(hits)

    return hits, cumulated_chars


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

        points =  parse_prescription(treat_qty)
        qty_prescription +=  render_prescription(points)

        points =  parse_prescription(treat_qual)
        qual_prescription +=  render_prescription(points)

        if pulse_yinyang:
            meridian_rel_yinyang_lvl = True  # meridian relative yinyang level
            prescription_list = meridian_yinyang(pulse_yinyang)

            points =  parse_prescription(prescription_list)
            meridian_prescription +=  render_prescription(points)

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

    preventive_prescription = []  # prescriptions list
    treatment_prescription = []
    knot_prescription = []

    preventive_logic = None

    if prevent:
        
        for pathogen in prevent:
               
            avert = Phenomena(pathogen)
            avert.preventive_method = method
            prescription = avert.phenom_prevent()
            pathogen_label = "防" + avert.pathogen
            formula = parse_prescription(prescription)
            formula = render_prescription(formula)
            preventive_prescription.append([pathogen_label, zip(formula, avert.logic_prevent)])

    if treat:
        
        for pathogen in treat:
            cure = Phenomena(pathogen)
            prescription = cure.phenom_treat()
            pathogen_label = "袪" + cure.pathogen
            formula = parse_prescription(prescription)
            formula = render_prescription(formula)
            treatment_prescription.append((pathogen_label, zip(formula, cure.logic_treat)))

    if knot:

        link = Phenomena()
        knot_points = [link.root_knot(k) for k in knot]

        for zh, tr, prescription in knot_points:
            knot_label = "連接" + zh + "經"
            points = parse_prescription([prescription])
            knot_prescription.append((knot_label, render_prescription(points)))

    if all([not treat, not prevent, not knot]):
        return render(request, template_name='data_assist/channels.html')
    else:
        return render(request, template_name='data_assist/channels.html',
                      context={
                          "result": True,
                          "prevent": prevent,
                          "treat": treat,
                          "knot": knot,
                          "prescription_preventive": preventive_prescription,
                          "prescription_treatment": treatment_prescription,
                          "prescription_knot": knot_prescription,
                          "logic_preventive": preventive_logic,
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
    cities_zh = ['阿布扎比', '阿德萊德', '阿拉木圖', '阿姆斯特丹', '安特衛普', '阿爾胡斯', '雅典', '亞特蘭大', '奧克蘭',
                 '巴爾的摩', '班加羅爾', '曼谷', '巴塞羅那',
                 '北京', '柏林', '伯明翰', '波哥大', '博洛尼亞', '波士頓', '布拉迪斯拉發', '巴西', '布里斯班',
                 '布魯塞爾', '布加勒斯特', '布達佩斯', '布宜諾斯艾利斯',
                 '開羅', '卡爾加里', '開普敦', '加拉加斯', '芝加哥', '克利夫蘭', '科隆', '科倫坡', '哥倫布', '哥本哈根',
                 '達拉斯', '底特律', '德累斯頓', '迪拜',
                 '都柏林', '杜塞爾多夫', '愛丁堡', '法蘭克福', '日內瓦', '熱那亞', '格拉斯哥', '哥德堡', '廣州', '漢堡',
                 '河內', '赫爾辛基', '胡志明市', '香港',
                 '休斯頓', '伊斯坦布爾', '雅加達', '約翰內斯堡', '堪薩斯城', '基輔', '吉隆坡', '利茲', '里爾', '利馬',
                 '里斯本', '倫敦', '洛杉磯', '盧森堡',
                 '里昂', '馬德里', '曼徹斯特', '馬尼拉', '馬賽', '墨爾本', '墨西哥城', '邁阿密', '米蘭', '明尼阿波利斯',
                 '蒙得維的亞', '蒙特利爾', '莫斯科', '孟買',
                 '慕尼黑', '新德里', '紐約', '大阪', '奧斯陸', '巴黎', '費城', '布拉格', '里士滿', '里約熱內盧',
                 '利雅得', '羅馬', '鹿特丹', '舊金山', '聖地亞哥',
                 '聖保羅', '西雅圖', '首爾', '上海', '新加坡', '聖彼得堡', '斯德哥爾摩', '斯圖加特', '悉尼', '台北',
                 '塔什幹', '德黑蘭', '特拉維夫', '海牙',
                 '蒂華納', '東京', '多倫多', '都靈', '烏得勒支', '溫哥華', '維也納', '華沙', '華盛頓', '惠靈頓',
                 '蘇黎世']

    cities_zh_labels = zip(cities, cities_zh)

    solartime, timezone = solartime_by_ip()

    timezone = pytz.timezone(timezone)
    dt_aware = datetime.now(timezone)

    curr_loc_hr = solartime.datetime().strftime("%H")
    hr_name, hr_meridian_id, hr_meridian = get_horary(curr_loc_hr)

    city = request.GET.get('city')
    # TODO: Fix bug - some cities eg. Taipei, Beijing return null value.

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

        depart_info_noted = request.GET.get('depart_info_noted')

        if prescription:

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

            if depart_info_noted:
                if depart_info_noted != city:
                    return render(request, template_name='data_assist/horary.html',
                                  context={
                                      "city_selected": city,
                                      "city_selected_zh": cities_zh[cities.index(city)],
                                      "depart_time": dt_depart.strftime("%x  %X"),
                                      "depart_timezone": depart_tz,
                                      "depart_solar_time": str(depart_solar),
                                      "depart_hour": depart_hr_name,
                                      "depart_meridian": depart_hr_meridian,
                                      "local_time": dt_aware.strftime("%x  %X"),
                                      "local_timezone": timezone,
                                      "local_solar_time": str(solartime),
                                      "local_hour": hr_name,
                                      "local_meridian": hr_meridian,
                                      "cities": cities,
                                      "cities_zh": cities_zh_labels,
                                  })
                else:
                    return render(request, template_name='data_assist/horary.html',
                                  context={
                                      "result": True,
                                      "depart": True,
                                      "city_selected": city,
                                      "city_selected_zh": cities_zh[cities.index(city)],
                                      "depart_time": dt_depart.strftime("%x  %X"),
                                      "depart_timezone": depart_tz,
                                      "depart_solar_time": str(depart_solar),
                                      "depart_hour": depart_hr_name,
                                      "depart_meridian": depart_hr_meridian,
                                      "local_time": dt_aware.strftime("%x  %X"),
                                      "local_timezone": timezone,
                                      "local_solar_time": str(solartime),
                                      "local_hour": hr_name,
                                      "local_meridian": hr_meridian,
                                      "cities": cities,
                                      "cities_zh": cities_zh_labels,
                                      "luo": luo_rendered,
                                      "luo_desc": luo_desc,
                                      "transfer": list(zip(transfer_desc, transfer_rendered)),
                                  })

            else:
                return render(request, template_name='data_assist/horary.html',
                              context={
                                  "depart": True,
                                  "city_selected": city,
                                  "city_selected_zh": cities_zh[cities.index(city)],
                                  "local_time": dt_aware.strftime("%x  %X"),
                                  "local_timezone": timezone,
                                  "local_solar_time": str(solartime),
                                  "local_hour": hr_name,
                                  "local_meridian": hr_meridian,
                                  "depart_time": dt_depart.strftime("%x  %X"),
                                  "depart_timezone": depart_tz,
                                  "depart_solar_time": str(depart_solar),
                                  "depart_hour": depart_hr_name,
                                  "depart_meridian": depart_hr_meridian,
                                  "cities": cities,
                                  "cities_zh": cities_zh_labels,
                              })

        else:
            return render(request, template_name='data_assist/horary.html',
                          context={
                              "city_selected": city,
                              "city_selected_zh": cities_zh[cities.index(city)],
                              "depart_time": dt_depart.strftime("%x  %X"),
                              "depart_timezone": depart_tz,
                              "depart_solar_time": str(depart_solar),
                              "depart_hour": depart_hr_name,
                              "depart_meridian": depart_hr_meridian,
                              "local_time": dt_aware.strftime("%x  %X"),
                              "local_timezone": timezone,
                              "local_solar_time": str(solartime),
                              "local_hour": hr_name,
                              "local_meridian": hr_meridian,
                              "cities": cities,
                              "cities_zh": cities_zh_labels,
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
                          "cities_zh": cities_zh_labels,
                      })


def elements(request):
    
    # 五行
    organ_energy = request.GET.get("organEnergy")
    mother_energy = request.GET.get("motherEnergy")
    son_energy = request.GET.get("sonEnergy")
    minister_energy = request.GET.get("ministerEnergy")

    def relative_data(mother_status, son_status, minister_status):
        excess_energy = []
        deficient_energy = []

        if mother_status == "-":
            deficient_energy.append("mother")
        elif mother_status == "+":
            excess_energy.append("mother")

        if son_status == "-":
            deficient_energy.append("son")
        elif son_status == "+":
            excess_energy.append("son")

        if minister_status == "-":
            deficient_energy.append("minister")
        elif minister_status == "+":
            excess_energy.append("minister")

        return excess_energy, deficient_energy

    excess, deficient = relative_data(mother_energy, son_energy, minister_energy)

    # sp_energy = request.GET.get("spEnergy")
    treat_sp = request.GET.get("sp_choice")

    s = Season()
    this_season = s.current_season()
    lord_id = s.seasonal_lord(this_season[0])

    a = Acute()
    season_lord = "－".join(a.organ_viscera_zh(lord_id))
    season_lord_id = lord_id

    if treat_sp == "SP":
        lord_id = "SP"

    jun = Lord(lord_id)

    mother = "－".join(a.organ_viscera_zh(jun.mother))
    son = "－".join(a.organ_viscera_zh(jun.son))
    minister = "－".join(a.organ_viscera_zh(jun.minister))
    inhibited = "－".join(a.organ_viscera_zh(jun.inhibited))
    lord = "－".join(a.organ_viscera_zh(lord_id))

    earth_energy = s.earth_energy_timeframe(this_season[1])

    G, graph = a.graph()

    # if earth_energy:
    #     sp = Lord("SP")
    #     earth_lord = "－".join(a.organ_viscera_zh("SP"))
    #     earth_mother = "－".join(a.organ_viscera_zh(sp.mother))
    #     earth_son = "－".join(a.organ_viscera_zh(sp.son))
    #     earth_minister = "－".join(a.organ_viscera_zh(sp.minister))
    #     earth_inhibited = "－".join(a.organ_viscera_zh(sp.inhibited))
    # else:
    #     earth_lord = earth_mother = earth_son = earth_minister = earth_inhibited = None

    if organ_energy is None:
        return render(request, template_name='data_assist/elements.html',
                      context={
                          "season": this_season,
                          "season_lord_id": season_lord_id,
                          "season_lord": season_lord,
                          "lord_id": lord_id,
                          "lord": lord,
                          "mother": mother,
                          "son": son,
                          "minister": minister,
                          "inhibited": inhibited,
                          "earth_energy": earth_energy,
                          "treat_sp": treat_sp,
                          # "E_lord": earth_lord,
                          # "E_mother": earth_mother,
                          # "E_son": earth_son,
                          # "E_minister": earth_minister,
                          # "E_inhibited": earth_inhibited,
                          "graph": graph,
                      })
    else:

        p = Pentashu()
        prescribe = a.diagnose(lord_id, organ_energy, excess=excess, deficient=deficient)

        treatment = []

        for logic, formula in prescribe:

            attrib = []

            try:
                comma = logic.index("，")
                logic = logic[:comma] + "<br>" + logic[comma:]
            except ValueError:
                pass

            for pt, act in formula:
                attrib_raw = p.get_attributes(pt)
                attrib_tagged = "<br class='d-sm-none'>（" + attrib_raw + "）"
                attrib.append(attrib_tagged)

            formula = parse_prescription(formula)
            formula = render_prescription(formula)

            treatment.append([logic, list(zip(formula, attrib))])

        return render(request, template_name='data_assist/elements.html',
                      context={
                          "season": this_season,
                          "season_lord_id": season_lord_id,
                          "season_lord": season_lord,
                          "lord_id": lord_id,
                          "lord": lord,
                          "mother": mother,
                          "son": son,
                          "minister": minister,
                          "inhibited": inhibited,
                          "earth_energy": earth_energy,
                          # "E_lord": earth_lord,
                          # "E_mother": earth_mother,
                          # "E_son": earth_son,
                          # "E_minister": earth_minister,
                          # "E_inhibited": earth_inhibited,
                          "graph": graph,
                          "prescription": treatment,
                          "result": True,
                      })


def mushu(request):
    # 募俞穴

    lord = request.POST.get("organ")
    state = request.POST.get("energy")

    s = Season()
    this_season = s.current_season()
    season_lord_id = s.seasonal_lord(this_season[0])

    ch = Chronic()
    ch.som_emo = request.POST.get("som_emo")
    ch.jb_func = request.POST.get("jb_func")

    organ_labels = [(k, v) for k, v in ch.organ_viscera_zh_map.items()]
    seasonal_lord = ch.organ_viscera_zh_map[season_lord_id]

    G, graph = ch.graph()

    if ch.som_emo and ch.jb_func:

        diagnosis = ch.organ_viscera_zh_map[lord] + ["實" if state == "+" else "虛"][0]
        formula, logic = ch.diagnose(lord, state)
        prescription = [point for point, desc in [i for i in formula if i is not None]]
        description = [desc for point, desc in [i for i in formula if i is not None]]
        logic = [i for i in logic if i is not None]

        prescription =  parse_prescription(prescription)
        prescription =  render_prescription(prescription)

        treatment = zip(prescription, description, logic)

        return render(request, template_name='data_assist/mushu.html',
                      context={
                          "mushu": True,
                          "result": True,
                          "som_emo": ch.som_emo,
                          "jb_func": ch.jb_func,
                          "heading": ch.som_emo + "性臟腑－" + ch.jb_func,
                          "season": this_season,
                          "season_lord_id": season_lord_id,
                          "season_lord": seasonal_lord,
                          "lord": lord,
                          "organs_list": organ_labels,
                          "graph": graph,
                          "diagnosis": diagnosis,
                          "treatment": treatment,
                      })
    else:

        return render(request, template_name='data_assist/mushu.html',
                      context={
                          "mushu": True,
                          "season": this_season,
                          "season_lord_id": season_lord_id,
                          "season_lord": seasonal_lord,
                          "organs_list": organ_labels,
                          "graph": graph,
                      })


def extraordinary(request):
    meridian_id = request.GET.get("target_meridian")

    ex = Extraordinary()
    meridian_list = ex.labels()

    if meridian_id:

        ex = Extraordinary(meridian_id)

        rel_state = request.GET.get("rel_state") == meridian_id

        meridian_name = ex.id_to_meridian_name(meridian_id, abbrev=True)

        relative_states = ex.diagnose_deficiency()

        rel_state_labels = []
        for grp in relative_states:
            rel_state_labels.append(parse_state(grp, meridian=True, abbrev=True))

        if rel_state:
            prescription = list(ex.treatment())
            bypass_candidates = parse_prescription(prescription[0], "zh")

            jiaohuixue_in_use = request.GET.getlist("meeting_pts")

            if jiaohuixue_in_use:

                prescription[0] = [(pt, action) for pt, action in prescription[0] if pt in jiaohuixue_in_use]
                parsed_prescription = [parse_prescription(p, "zh") for p in prescription]

                rendered_prescription = [render_prescription(p) for p in parsed_prescription]
                jiaohuixue, bamai = rendered_prescription

                rel_state_labels = [list(label_lst) for label_lst in rel_state_labels]
                ex_meridian = "".join(rel_state_labels[0][1][1:])
                target = rel_state_labels[0][1][1] + "－" + rel_state_labels[0][0][1]
                complement = ex.id_to_meridian_name(ex.paired_ex_meridian, abbrev=True) + "－" + \
                             ex.id_to_meridian_name(ex.paired_meridian, abbrev=True)
                opposite = rel_state_labels[1][1][1] + "－" + rel_state_labels[1][0][1]
                opposite_complement = ex.id_to_meridian_name(ex.opp_paired_ex_meridian, abbrev=True) + "－" + \
                                      ex.id_to_meridian_name(ex.opp_paired_meridian, abbrev=True)

                bamai_attrib = [
                    target,
                    complement + "<br>【相配】",
                    opposite + "<br>【對側】",
                    opposite_complement + "<br>【對側相配】",
                ]

                bamai = zip(bamai, bamai_attrib)

                return render(request, template_name='data_assist/extraordinary.html',
                              context={
                                  "result": True,
                                  "rel_state": True,
                                  "meridian": True,
                                  "ex_meridian": ex_meridian,
                                  "meridian_id": meridian_id,
                                  "meridian_name": meridian_name,
                                  "meridian_list": meridian_list,
                                  "relative_states": rel_state_labels,
                                  "bypass": bypass_candidates,
                                  "jiaohuixue": jiaohuixue,
                                  "bamai": bamai,
                              })

            else:
                return render(request, template_name='data_assist/extraordinary.html',
                              context={
                                  "rel_state": True,
                                  "meridian": True,
                                  "meridian_id": meridian_id,
                                  "meridian_name": meridian_name,
                                  "meridian_list": meridian_list,
                                  "relative_states": rel_state_labels,
                                  "bypass": bypass_candidates,
                              })

        else:
            return render(request, template_name='data_assist/extraordinary.html',
                          context={
                              "meridian": True,
                              "meridian_id": meridian_id,
                              "meridian_name": meridian_name,
                              "meridian_list": meridian_list,
                              "relative_states": rel_state_labels,
                          })

    else:
        return render(request, template_name='data_assist/extraordinary.html',
                      context={
                          "meridian_list": meridian_list,
                      })


def jingjin(request):
    # 經筋
    return render(request, template_name='data_assist/jingjin.html')


def jingbie(request):
    # 經別
    return render(request, template_name='data_assist/jingbie.html')


def luo(request):
    category = request.GET.get("lat_lon")

    luo = Luo()
    meridian_lbl = luo.meridian_label()

    if category:
        if category == "balance":
            category_lbl = "橫絡"

            meridian = request.GET.get("meridian")
            state = request.GET.get("state")

            if all([meridian, state]):

                rel_state = request.GET.get("rel_state") == meridian

                luo = Luo(meridian, state)
                luo.balance()

                relative_states = luo.relative_state_label

                rel_state_labels = parse_state(relative_states, meridian=True, abbrev=True)

                if rel_state:

                    prescription = luo.prescribe

                    prescription = parse_prescription(prescription)
                    prescription = render_prescription(prescription)

                    logic = luo.logic

                    treatment = zip(prescription, logic)

                    return render(request, template_name='data_assist/luo.html',
                                  context={  # Balance Result
                                      "result": True,
                                      "balance": True,
                                      "meridian": meridian,
                                      "meridian_name": id_to_meridian_name(meridian, abbrev=True),
                                      "meridian_state": state,
                                      "relative_states": rel_state_labels,
                                      "category": category,
                                      "category_lbl": category_lbl,
                                      "meridian_list": meridian_lbl,
                                      "prescription": treatment,
                                  })
                else:
                    return render(request, template_name='data_assist/luo.html',
                                  context={  # No relative state; ready for input
                                      "meridian": meridian,
                                      "meridian_name": id_to_meridian_name(meridian, abbrev=True),
                                      "meridian_state": state,
                                      "category": category,
                                      "category_lbl": category_lbl,
                                      "meridian_list": meridian_lbl,
                                      "relative_states": rel_state_labels,
                                  })

            else:
                return render(request, template_name='data_assist/luo.html',
                              context={  # No meridian
                                  "category": category,
                                  "category_lbl": category_lbl,
                                  "meridian_list": meridian_lbl,
                              })

# =========================================================

        elif category == "symptom":

            category_lbl = "縱絡"
            symptom_query = request.GET.get("symptom_query")
            symptom = request.GET.get("symptom")
            confirm = request.GET.get("symptom_confirm")

            prescription = request.GET.get("prescription")  # stored in hidden input tag.
            diagnosis = request.GET.get("diagnosis")
            symptom_id = request.GET.get("symptom_id")

            if symptom_id and not symptom:

                luo = Luo()
                luo.select_symptom(symptom_id[:-1], symptom_id[-1])
                prescription = luo.treat_symptom()
                logic = luo.logic

                target, state = luo.target_luo
                symptom = target[0][-1]
                meridian = target[0][2]
                diagnosis = "".join(parse_state([(meridian, state)], abbrev=True))

                prescription = parse_prescription(prescription)
                prescription = render_prescription(prescription)

                treatment = zip(prescription, logic)

                return render(request, template_name='data_assist/luo.html',
                              context={  # Symptom Result via radio-button; after query yields multiple possibilities.
                                  "result": True,
                                  "symptom": symptom,
                                  "symptom_id": symptom_id,
                                  "diagnosis": diagnosis,
                                  "prescription": treatment,
                              })

            elif prescription:  # for Symptom Result via single query below.
                prescription = eval(prescription)  # convert text to code.

                if symptom and confirm:
                    return render(request, template_name='data_assist/luo.html',
                                  context={  # Symptom Result via Single Query.
                                      "result": True,
                                      "symptom": symptom,
                                      "symptom_id": confirm,
                                      "diagnosis": diagnosis,
                                      "prescription": prescription,
                                  })

# =========================================================

            elif symptom_query:  # query input.

                luo = Luo()
                found = luo.locate_symptom(symptom_query)

                if luo.target_luo:  # target found.

                    query_str = symptom_query

                    target, state = luo.target_luo
                    symptom_id = target[0][0] + state
                    symptom = target[0][-1]
                    meridian = target[0][2]
                    diagnosis = "".join(parse_state([(meridian, state)], abbrev=True))

                    prescription = luo.treat_symptom()
                    logic = luo.logic

                    prescription = parse_prescription(prescription)
                    prescription = render_prescription(prescription)

                    treatment = zip(prescription, logic)

                    return render(request, template_name='data_assist/luo.html',
                                  context={  # return single target,
                                      # pass variables into hidden tags within luo_symptom_found.html.
                                      "found_target": True,
                                      "query_str": query_str,
                                      "target": luo.target_luo,
                                      "category": category,
                                      "category_lbl": category_lbl,
                                      "symptom": symptom,
                                      "symptom_id": symptom_id,
                                      "diagnosis": diagnosis,
                                      "prescription": list(treatment),
                                  })

                elif found:  # query yields multiple results.

                    excess = deficient = None

                    if found[0] not in ["+", "-"]:
                        excess, deficient = found
                    elif found[0] == "+":
                        excess = found[1]
                    elif found[0] == "-":
                        deficient = found[1]

                    return render(request, template_name='data_assist/luo.html',
                                  context={  # Return multiple results radio-button query form.
                                      "found": True,
                                      "found_multiple": True,
                                      "category": category,
                                      "category_lbl": category_lbl,
                                      "excess": excess,
                                      "deficient": deficient,
                                  })

                else:  # query NOT FOUND.
                    return render(request, template_name='data_assist/luo.html',
                                  context={
                                      "category": category,
                                      "category_lbl": category_lbl,
                                  })

            else:  #
                return render(request, template_name='data_assist/luo.html',
                              context={
                                  "category": category,
                                  "category_lbl": category_lbl,
                              })

    else:  # no query input.
        return render(request, template_name='data_assist/luo.html')  # basic - no category


def group_luo(request):

    category = request.GET.get("category")

    if category:

        lbl_category = "疼痛" if category == "pain" else "半身不遂"

        if category == "pain":

            left_right = request.GET.get("left_right")
            top_bottom = request.GET.get("top_bottom")
            yinyang = int(request.GET.get("yinyang")) if request.GET.get("yinyang") else None

            lbl_left_right = "左側" if left_right == "l" else "右側" if left_right == "r" else None
            lbl_top_bottom = "上半身" if top_bottom == "t" else "下半身" if top_bottom == "b" else None
            lbl_yinyang = "陰痛" if yinyang == 0 else "陽痛" if yinyang == 1 else None

            if all([left_right, top_bottom, lbl_yinyang]):

                gl = GroupLuo(left_right, top_bottom, yinyang)
                prescribe = gl.pain()

                prescription = [p for p, pos in prescribe]
                position = [pos for p, pos in prescribe]
                position_labels = ["左側" if pos == "l" else "右側" for pos in position]

                prescription = parse_prescription(prescription)
                prescription = render_prescription(prescription)

                treatment = zip(position_labels, prescription)

                return render(request, template_name='data_assist/group_luo.html',
                              context={
                                  "result": True,
                                  "category": category,
                                  "category_lbl": lbl_category,
                                  "ailment_lbl": lbl_top_bottom + lbl_left_right + lbl_yinyang,
                                  "prescription": treatment,
                              })

            else:

                return render(request, template_name='data_assist/group_luo.html',
                              context={
                                  "category": category,
                                  "category_lbl": lbl_category,
                              })

        elif category == "hemiplegia":

            left_right = request.GET.get("left_right")
            yinyang = request.GET.get("yinyang")

            lbl_left_right = "左側" if left_right == "l" else "右側" if left_right == "r" else None
            lbl_yinyang = "鬆弛無力型" if yinyang == "atonic" else "攣縮型" if yinyang == "spastic" else None

            if all([left_right, yinyang]):

                gl = GroupLuo(left_right, nature=yinyang, hemiplegia=True)
                prescribe = gl.hemiplegia()

                prescription = [p for p, pos in prescribe]
                position = [pos for p, pos in prescribe]
                position_labels = ["左側" if pos == "l" else "右側" for pos in position]

                prescription = parse_prescription(prescription)
                prescription = render_prescription(prescription)

                treatment = zip(position_labels, prescription)

                return render(request, template_name='data_assist/group_luo.html',
                              context={
                                  "result": True,
                                  "category": category,
                                  "category_lbl": lbl_category,
                                  "ailment_lbl": lbl_left_right + lbl_yinyang + "<br>" + lbl_category,
                                  "prescription": treatment,
                              })
            else:
                return render(request, template_name='data_assist/group_luo.html',
                              context={
                                  "category": category,
                                  "category_lbl": lbl_category,
                              })

        else:

            return render(request, template_name='data_assist/group_luo.html',
                          context={
                              "category": category,
                              "category_lbl": lbl_category,
                          })

    else:
        return render(request, template_name='data_assist/group_luo.html')


if __name__ == '__main__':
    pass
