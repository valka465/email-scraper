import streamlit as st
import pandas as pd
import requests
import asyncio
import aiohttp
import nest_asyncio

def get_available_concurrency(api_key):
    url = "https://api.hasdata.com/user/me/usage"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("data", {}).get("availableConcurrency", 1)
    else:
        st.error(f"Error for concurrency: {response.status_code}")
        return 1

def get_sites_from_serp(keywords, api_key, country, language, num_res):
    urls = []
    for kw in keywords:
        response = requests.get(
            "https://api.hasdata.com/scrape/google-light/serp",
            headers={"x-api-key": api_key},
            params={"q": kw, "gl": country, "hl": language, "num": num_res}
        )
        if response.status_code == 200:
            data = response.json()
            organic_results = data.get("organicResults", [])
            for item in organic_results:  
                url = item.get("link")
                if url:
                    urls.append(url)
        else:
            print(f"Error for keyword '{kw}': {response.status_code}")
    return urls


def get_sites_from_maps(keywords, api_key, language):
    results = []
    for kw in keywords:
        response = requests.get(
            "https://api.hasdata.com/scrape/google-maps/search",
            headers={"x-api-key": api_key},
            params={"q": kw, "hl": language}
        )
        if response.status_code == 200:
            data = response.json()
            for place in data.get("localResults", []):
                website = place.get("website")
                address = place.get("address")
                phone = place.get("phone")
                if website or address or phone:
                    results.append({
                        "website": website,
                        "address": address,
                        "phone": phone
                    })
    return results

def normalize_url(url):
    if not url.startswith(("http://", "https://")):
        return "http://" + url
    return url

def universe_url(url):
    try:
        url = url.strip().lower()
        if not url.startswith("http"):
            url = "http://" + url
        url = url.replace("https://", "http://")
        url = url.replace("www.", "")
        if url.endswith("/"):
            url = url[:-1]

    except Exception as e:
        pass
    return url

nest_asyncio.apply()

async def scrape_single_site(session, url, api_key, country, proxy, semaphore=None):
    if semaphore:
        async with semaphore:
            return await scrape_single_site(session, url, api_key, country, proxy, semaphore=None)

    normalized_url = url if url.startswith(("http://", "https://")) else "http://" + url

    payload = {
        "url": normalized_url,
        "extractEmails": True,
        "js_rendering": True,
        "aiExtractRules": {
            "address": {"description": "Physical address", "type": "string"},
            "phone": {"description": "Phone number", "type": "string"},
            "email": {"description": "Email addresses", "type": "string"},
            "companyName": {"description": "Company name", "type": "string"}
        }
    }
    if proxy:
        payload["proxyType"] = proxy
    if country:
        payload["proxyCountry"] = country.upper()

    async with session.post(
        "https://api.hasdata.com/scrape/web",
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json"
        },
        json=payload
    ) as response:
        if response.status == 200:
            data = await response.json()
            emails_list = data.get("emails", [])
            ai_resp = data.get("aiResponse", {})

            company = ai_resp.get("companyName", "-")
            address = ai_resp.get("address", "-")
            phone = ai_resp.get("phone", "-")
            email_ai = ai_resp.get("email", "")

            all_emails = set(emails_list)
            if email_ai:
                all_emails.add(email_ai)

            email_combined = ", ".join(all_emails) if all_emails else ""

            return {
                "Website": url,
                "Email": email_combined,
                "Company Name": company,
                "Address": address,
                "Phone": phone
            }
        else:
            text = await response.text()
            print(f"Error for {url}: {text}")
            return {
                "Website": url,
                "Email": "error",
                "Company Name": "-",
                "Address": "-",
                "Phone": "-"
            }

async def scrape_contacts_from_sites_async(urls, api_key, country, proxy):
    concurrency = get_available_concurrency(api_key)
    semaphore = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession() as session:
        tasks = [scrape_single_site(session, url, api_key, country, proxy, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
    return results

def run_scraping(urls, api_key, country, proxy):
    return asyncio.run(scrape_contacts_from_sites_async(urls, api_key, country, proxy))


proxy_countries = {
    "us": "United States",
    "uk": "United Kingdom",
    "de": "Germany",
    "ie": "Ireland",
    "fr": "France",
    "it": "Italy",
    "se": "Sweden",
    "br": "Brazil",
    "ca": "Canada",
    "jp": "Japan",
    "sg": "Singapore",
    "in": "India",
    "id": "Indonesia"
}


countries = {
    "us": "United States","af": "Afghanistan", "al": "Albania", "dz": "Algeria", "as": "American Samoa",
    "ad": "Andorra","ao": "Angola","ai": "Anguilla","aq": "Antarctica",
    "ag": "Antigua and Barbuda","ar": "Argentina","am": "Armenia",
    "aw": "Aruba","au": "Australia","at": "Austria","az": "Azerbaijan",
    "bs": "Bahamas","bh": "Bahrain","bd": "Bangladesh","bb": "Barbados",
    "by": "Belarus","be": "Belgium","bz": "Belize","bj": "Benin",
    "bm": "Bermuda","bt": "Bhutan","bo": "Bolivia","ba": "Bosnia and Herzegovina",
    "bw": "Botswana","bv": "Bouvet Island","br": "Brazil","io": "British Indian Ocean Territory",
    "bn": "Brunei Darussalam","bg": "Bulgaria","bf": "Burkina Faso",
    "bi": "Burundi","kh": "Cambodia","cm": "Cameroon","ca": "Canada",
    "cv": "Cape Verde","ky": "Cayman Islands","cf": "Central African Republic",
    "td": "Chad","cl": "Chile","cn": "China","cx": "Christmas Island","cc": "Cocos (Keeling) Islands",
    "co": "Colombia","km": "Comoros","cg": "Congo","cd": "Congo, the Democratic Republic of the",
    "ck": "Cook Islands","cr": "Costa Rica","ci": "Cote D'ivoire","hr": "Croatia",
    "cu": "Cuba","cy": "Cyprus","cz": "Czech Republic","dk": "Denmark",
    "dj": "Djibouti","dm": "Dominica","do": "Dominican Republic","ec": "Ecuador",
    "eg": "Egypt","sv": "El Salvador","gq": "Equatorial Guinea","er": "Eritrea",
    "ee": "Estonia","et": "Ethiopia","fk": "Falkland Islands (Malvinas)",
    "fo": "Faroe Islands","fj": "Fiji","fi": "Finland","fr": "France",
    "gf": "French Guiana","pf": "French Polynesia",
    "tf": "French Southern Territories","ga": "Gabon","gm": "Gambia",
    "ge": "Georgia","de": "Germany","gh": "Ghana","gi": "Gibraltar",
    "gr": "Greece","gl": "Greenland","gd": "Grenada","gp": "Guadeloupe",
    "gu": "Guam","gt": "Guatemala","gn": "Guinea","gw": "Guinea-Bissau",
    "gy": "Guyana","ht": "Haiti","hm": "Heard Island and Mcdonald Islands",
    "va": "Holy See (Vatican City State)","hn": "Honduras","hk": "Hong Kong",
    "hu": "Hungary","is": "Iceland","in": "India","id": "Indonesia",
    "ir": "Iran, Islamic Republic of","iq": "Iraq","ie": "Ireland",
    "il": "Israel","it": "Italy","jm": "Jamaica","jp": "Japan",
    "jo": "Jordan","kz": "Kazakhstan","ke": "Kenya","ki": "Kiribati",
    "kp": "Korea, Democratic People's Republic of","kr": "Korea, Republic of","kw": "Kuwait",
    "kg": "Kyrgyzstan","la": "Lao People's Democratic Republic",
    "lv": "Latvia","lb": "Lebanon","ls": "Lesotho","lr": "Liberia",
    "ly": "Libyan Arab Jamahiriya","li": "Liechtenstein","lt": "Lithuania","lu": "Luxembourg",
    "mo": "Macao","mk": "Macedonia, the Former Yugoslav Republic of",
    "mg": "Madagascar","mw": "Malawi","my": "Malaysia","mv": "Maldives",
    "ml": "Mali","mt": "Malta","mh": "Marshall Islands","mq": "Martinique",
    "mr": "Mauritania","mu": "Mauritius","yt": "Mayotte","mx": "Mexico",
    "fm": "Micronesia, Federated States of","md": "Moldova, Republic of",
    "mc": "Monaco","mn": "Mongolia","ms": "Montserrat","ma": "Morocco",
    "mz": "Mozambique","mm": "Myanmar","na": "Namibia","nr": "Nauru",
    "np": "Nepal","nl": "Netherlands","nz": "New Zealand","ni": "Nicaragua",
    "ne": "Niger","ng": "Nigeria","nu": "Niue","nf": "Norfolk Island",
    "mp": "Northern Mariana Islands","no": "Norway","om": "Oman",
    "pk": "Pakistan","pw": "Palau","pa": "Panama","pg": "Papua New Guinea",
    "py": "Paraguay","pe": "Peru","ph": "Philippines","pl": "Poland",
    "pt": "Portugal","pr": "Puerto Rico",
    "qa": "Qatar","ro": "Romania","ru": "Russian Federation","rw": "Rwanda"
}

languages = {
    "en": "English","af": "Afrikaans","ak": "Akan","sq": "Albanian","ws": "Samoa",
    "am": "Amharic","ar": "Arabic","hy": "Armenian","az": "Azerbaijani",
    "eu": "Basque","be": "Belarusian","bem": "Bemba","bn": "Bengali",
    "bh": "Bihari","bs": "Bosnian","br": "Breton","bg": "Bulgarian",
    "bt": "Bhutanese","km": "Cambodian","ca": "Catalan","chr": "Cherokee",
    "ny": "Chichewa","zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)","co": "Corsican","hr": "Croatian",
    "cs": "Czech","da": "Danish","nl": "Dutch",
    "eo": "Esperanto","et": "Estonian","ee": "Ewe","fo": "Faroese",
    "tl": "Filipino","fi": "Finnish","fr": "French","fy": "Frisian",
    "gaa": "Ga","gl": "Galician","ka": "Georgian","de": "German",
    "el": "Greek","kl": "Greenlandic","gn": "Guarani","gu": "Gujarati",
    "ht": "Haitian Creole","ha": "Hausa","haw": "Hawaiian",
    "iw": "Hebrew","hi": "Hindi","hu": "Hungarian","is": "Icelandic",
    "ig": "Igbo","id": "Indonesian","ia": "Interlingua","ga": "Irish",
    "it": "Italian","ja": "Japanese","jw": "Javanese","kn": "Kannada",
    "kk": "Kazakh","rw": "Kinyarwanda","rn": "Kirundi","kg": "Kongo",
    "ko": "Korean","ku": "Kurdish","ckb": "Kurdish (Soranî)","ky": "Kyrgyz",
    "lo": "Laothian","la": "Latin","lv": "Latvian","ln": "Lingala",
    "lt": "Lithuanian","loz": "Lozi","lg": "Luganda","ach": "Luo",
    "mk": "Macedonian","mg": "Malagasy","my": "Malay","ml": "Malayalam",
    "mt": "Maltese","mv": "Maldives","mi": "Maori","mr": "Marathi",
    "mfe": "Mauritian Creole","mo": "Moldavian","mn": "Mongolian","sr-me": "Montenegrin",
    "ne": "Nepali","pcm": "Nigerian Pidgin","nso": "Northern Sotho","no": "Norwegian",
    "nn": "Norwegian (Nynorsk)","oc": "Occitan","or": "Oriya",
    "om": "Oromo","ps": "Pashto","fa": "Persian","pl": "Polish",
    "pt": "Portuguese","pt-br": "Portuguese (Brazil)","pt-pt": "Portuguese (Portugal)",
    "pa": "Punjabi","qu": "Quechua","ro": "Romanian","rm": "Romansh",
    "nyn": "Runyakitara","ru": "Russian","gd": "Scots Gaelic","sr": "Serbian",
    "sh": "Serbo-Croatian","st": "Sesotho","tn": "Setswana","crs": "Seychellois Creole",
    "sn": "Shona","sd": "Sindhi","si": "Sinhalese","sk": "Slovak",
    "sl": "Slovenian","so": "Somali","es": "Spanish","es-419": "Spanish (Latin American)",
    "su": "Sundanese","sw": "Swahili","sv": "Swedish","tg": "Tajik",
    "ta": "Tamil","tt": "Tatar","te": "Telugu","th": "Thai",
    "ti": "Tigrinya","to": "Tonga","lua": "Tshiluba","tum": "Tumbuka",
    "tr": "Turkish","tk": "Turkmen","tw": "Twi","ug": "Uighur",
    "uk": "Ukrainian","ur": "Urdu","uz": "Uzbek","vu": "Vanuatu",
    "vi": "Vietnamese","cy": "Welsh","wo": "Wolof","xh": "Xhosa",
    "yi": "Yiddish","yo": "Yoruba","zu": "Zulu"
}

proxy = {
    "datacenter": "datacenter",
    "residential": "residential"
}



# === UI Section ===
st.title("Email Scraper Tool")

api_key = st.text_input("Enter [HasData's](https://app.hasdata.com/sign-up&utm_source=streamlit) API key", type="password", 
                        help="Get your API key from HasData at [hasdata.com](https://app.hasdata.com/sign-up&utm_source=streamlit). It's free.")


mode = st.selectbox("Choose the method", ["List of URLs", "Google SERP Keywords", "Google Maps Keywords"])

user_input = ""
if mode == "List of URLs":
    user_input = st.text_area("Enter a list of URLs (one per line)")
    proxy = st.selectbox("Select proxy type", options=list(proxy.keys()), format_func=lambda x: proxy[x])
    proxy_country = st.selectbox("Select country", options=list(proxy_countries.keys()), format_func=lambda x: proxy_countries[x])

elif mode == "Google SERP Keywords":
    user_input = st.text_area("Enter keywords (one query per line)")
    country = st.selectbox("Select country", options=list(countries.keys()), format_func=lambda x: countries[x])
    language = st.selectbox("Select language", options=list(languages.keys()), format_func=lambda x: languages[x])
    num_res = st.slider("Number of results", min_value=10, max_value=50, value=10)

elif mode == "Google Maps Keywords":
    user_input = st.text_area("Enter keywords (one query per line)")
    language = st.selectbox("Select language", options=list(languages.keys()), format_func=lambda x: languages[x])


if "results" not in st.session_state:
    st.session_state.results = []

if st.button("Run"): 
    if api_key and user_input:
        max_concurrent = get_available_concurrency(api_key)

        keywords = user_input.strip().splitlines()

        if mode == "List of URLs":
            urls = keywords
            results = run_scraping(urls, api_key, proxy_country.upper(), proxy)

        elif mode == "Google SERP Keywords":
            urls = get_sites_from_serp(keywords, api_key, country, language, num_res)
            results = run_scraping(urls, api_key, "", "")
        elif mode == "Google Maps Keywords": 
            maps_data = get_sites_from_maps(keywords, api_key, language)
            
            urls = [item['website'] for item in maps_data if 'website' in item and item['website']]
            scraped_data = run_scraping(urls, api_key, "", "")
                      
            maps_dict = {universe_url(item['website']): item for item in maps_data}
            scraped_dict = {universe_url(item['Website']): item for item in scraped_data}

            results = []
            for site in urls:
                norm_site = universe_url(site)
                combined = {}

                if norm_site in scraped_dict:
                    combined.update(scraped_dict[norm_site])
                else:
                    combined['Website'] = site  

                if norm_site in maps_dict:
                    combined['Address'] = maps_dict[norm_site].get('address') or combined.get('Address', '')
                    combined['Phone'] = maps_dict[norm_site].get('phone') or combined.get('Phone', '')

                results.append(combined)

        else:
            results = []

        st.session_state.results = results

    else:
        st.warning("Please enter your API key and data.")

if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    st.success(f"Found {len(df)} results")
    st.dataframe(df)

    csv = df.to_csv(index=False).encode('utf-8')
    json_str = df.to_json(orient='records', force_ascii=False)
    json_bytes = json_str.encode('utf-8')

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Download CSV", data=csv, file_name="emails.csv", mime='text/csv')
    with col2:
        st.download_button("Download JSON", data=json_bytes, file_name="emails.json", mime='application/json')