from bs4 import BeautifulSoup, Tag
from dataclasses import asdict, dataclass, field
from datetime import datetime
from getuseragent import UserAgent #type: ignore
from http.cookiejar import MozillaCookieJar
from rich.logging import RichHandler
from rich import print_json
from urllib.parse import urlparse, urljoin
from typing import cast, Optional, List
import argparse
import json
import logging
import os
import random
import requests
import subprocess
import sys
import time
import tomllib
import tomlkit

@dataclass(kw_only=True)
class DefaultConfig:
	base_url: str = 'https://hutt.co'
	save_path: str = os.path.expanduser('~')

@dataclass
class Info:
	url: str
	description: str

@dataclass(kw_only=True)
class Post:
	id: str
	description: str

@dataclass(kw_only=True)
class Photo:
	id: str
	data: Info

@dataclass(kw_only=True)
class Video:
	id: str
	data: Info

@dataclass(kw_only=True)
class MetaObject:
	performer: str
	posts: List[Post] = field(default_factory=list)
	photos: List[Photo] = field(default_factory=list)
	videos: List[Video] = field(default_factory=list)

	def asdict(self) -> dict[str, object]:
		return {
			"posts": {post.id: post.description for post in self.posts},
			"photos": {photo.id: photo.data.__dict__ for photo in self.photos},
			"videos": {video.id: video.data.__dict__ for video in self.videos}
		}

logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
browser_list = ['chrome', 'firefox']
browser = random.choice(browser_list)
user_agent = str(UserAgent(browser, limit=1).list[0])

accents_dict = {
	'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
	'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
	'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
	'À': 'A', 'È': 'E', 'Ì': 'I', 'Ò': 'O', 'Ù': 'U',
	'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u',
	'Â': 'A', 'Ê': 'E', 'Î': 'I', 'Ô': 'O', 'Û': 'U',
	'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u', 'ÿ': 'y',
	'Ä': 'A', 'Ë': 'E', 'Ï': 'I', 'Ö': 'O', 'Ü': 'U', 'Ÿ': 'Y',
	'ã': 'a', 'Ã': 'A',
	'ñ': 'n', 'Ñ': 'N',
	'ç': 'c', 'Ç': 'C',
	'ß': 'ss',
	'æ': 'ae', 'Æ': 'AE',
	'ø': 'o', 'Ø': 'O',
	'œ': 'oe', 'Œ': 'OE',
	'å': 'a', 'Å': 'A',
	'ð': 'd', 'Ð': 'D',
	'þ': 'th', 'Þ': 'TH',
	'ú': 'u', 'Ú': 'U',
	'ý': 'y', 'Ý': 'Y',
	'đ': 'd', 'Đ': 'D',
	'ħ': 'h', 'Ħ': 'H',
	'ı': 'i', 'İ': 'I',
	'ł': 'l', 'Ł': 'L',
	'ń': 'n', 'Ń': 'N',
	'ŕ': 'r', 'Ŕ': 'R',
	'ś': 's', 'Ś': 'S',
	'ź': 'z', 'Ź': 'Z',
	'ż': 'z', 'Ż': 'Z',
	'š': 's', 'Š': 'S',
	'č': 'c', 'Č': 'C',
	'ř': 'r', 'Ř': 'R',
	'ž': 'z', 'Ž': 'Z',
	'ŭ': 'u', 'Ŭ': 'U',
	'ğ': 'g', 'Ğ': 'G',
	'ş': 's', 'Ş': 'S',
	'ĉ': 'c', 'Ĉ': 'C',
	'ĝ': 'g', 'Ĝ': 'G',
	'ĥ': 'h', 'Ĥ': 'H',
	'ĵ': 'j', 'Ĵ': 'J',
	'ŝ': 's', 'Ŝ': 'S',
	'ŭ': 'u', 'Ŭ': 'U',
	'ő': 'o', 'Ő': 'O',
	'ű': 'u', 'Ű': 'U',
	'ą': 'a', 'Ą': 'A',
	'ę': 'e', 'Ę': 'E',
	'ǫ': 'o', 'Ǫ': 'O',
	'ų': 'u', 'Ų': 'U',
	'ļ': 'l', 'Ļ': 'L',
	'ņ': 'n', 'Ņ': 'N',
	'ŗ': 'r', 'Ŗ': 'R',
	'ķ': 'k', 'Ķ': 'K',
	'ā': 'a', 'Ā': 'A',
	'ē': 'e', 'Ē': 'E',
	'ī': 'i', 'Ī': 'I',
	'ū': 'u', 'Ū': 'U',
	'ō': 'o', 'Ō': 'O',
	'ȳ': 'y', 'Ȳ': 'Y',
	'ə': 'e', 'Ə': 'E',
	"'": ''
}

table = str.maketrans(accents_dict)

def parse_huttpy() -> argparse.ArgumentParser:
	parser=argparse.ArgumentParser(prog='huttpy')
	parser.add_argument('url', nargs='+', help='url')
	parser.add_argument('--json', '-j', action='store_true', default=False, help='Outputs to a json file')
	parser.add_argument('--no-download', '-n', action='store_true', default=False, help='Scrapes information without downloading')
	parser.add_argument('--no-prompts', '-p', action='store_true', default=False, help='Does not prompt before downloading.')
	parser.add_argument('--skip-posts', '-s', action='store_true', default=False, help='Skips downloading/scraping the posts.')
	parser.add_argument('--skip-photos', '-t', action='store_true', default=False, help='Skips downloading/scraping the photos.')
	parser.add_argument('--skip-videos', '-v', action='store_true', default=False, help='Skips downloading/scraping the videos.')
	parser.add_argument('--output', '-o', default=os.path.join(os.path.expanduser('~'), 'Desktop', f'Hutt-Dict-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.json'), help='Specify output path for the metadata only (Defaults to Desktop). Use config for download path.')

	return parser

def load_toml() -> dict[str, str]:
	config_path: str = os.path.join(os.path.expanduser("~"), ".config", "huttpy")
	config_file = os.path.join(config_path, 'huttpy_config.toml')

	with open(config_file, 'rb') as f:
		toml_dict = tomllib.load(f)

	return toml_dict

def save_toml(toml_dict: dict[str, str], toml_path: str) -> None:

	with open(toml_path, 'w') as c:
		c.write(tomlkit.dumps(toml_dict))

def save_json(content: dict[str, object] | dict[str, str], path: str, indent: int = 4) -> None:

	with open(path, 'w', encoding='utf8') as json_file:
		json.dump(content, json_file, indent=indent)

def load_huttpy_config() -> dict[str, str]:
	default_config = DefaultConfig()
	config_path = os.path.join(os.path.expanduser("~"), ".config", "huttpy")
	config_file = os.path.join(config_path, 'huttpy_config.toml')

	if not os.path.isfile(config_file):
		os.makedirs(config_path, exist_ok=True)
		save_toml(asdict(default_config), config_file)

	return load_toml()

def load_session(cookies_path: str) -> requests.sessions.Session:
	cookie_jar = MozillaCookieJar(cookies_path)
	cookie_jar.load(ignore_discard=True, ignore_expires=True)
	session = requests.Session()
	session.cookies = cookie_jar #type: ignore

	return session

def make_request(url: str, session: requests.sessions.Session, referer: Optional[dict[str, str]]) -> requests.Response:
	headers = {'User-Agent': user_agent}

	if referer:
		headers.update(referer)

	return session.get(url, headers=headers)

def countdown(seconds: int, idx: int, total: int) -> None:

	if idx != total:
		logging.info(f'Sleeping for {seconds} seconds...')

		while seconds > 0:
			time.sleep(1)
			seconds -= 1

def make_dirs(config: dict[str, str], performer: str, photos_count: int, videos_count: int) -> None:

	if photos_count:
		directory1 = os.path.join(config['save_path'], performer, 'Images')
		os.makedirs(directory1, exist_ok=True)

	if videos_count:
		directory2 = os.path.join(config['save_path'], performer, 'Videos')
		os.makedirs(directory2, exist_ok=True)

def clean_string(string: str) -> str:
	intermediate_string1 = string.translate(table)
	intermediate_string2 = intermediate_string1.translate({ord(c): ' ' for c in intermediate_string1 if not c.isalnum()})

	return ' '.join(intermediate_string2.split())

def detect_text(element: Tag) -> str:

	if hasattr(element, 'text'):
		post_text = element.text

	else:
		post_text = ''

	return post_text

def get_hutt(session: requests.sessions.Session, meta_object: MetaObject, perf_id: int,  performer: str, base_url: str, skip_posts: bool = False, skip_photos: bool = False, skip_videos: bool = False) -> None:	
	media_types = ['photos', 'videos', 'view']
	headers = {'Referer': urljoin(base_url, performer), 'User-Agent': user_agent}

	for m in media_types:
		page = 0

		if (m == 'view' and not skip_posts) or (m == 'photos' and not skip_photos) or (m == 'videos' and not skip_videos):

			if m in ['photos', 'videos']:
				headers['Referer'] = f'{headers["Referer"]}{m}'

			while True:
				ajax_url = f'{base_url}/hutts/ajax-posts?page={page}&view={m}&id={perf_id}'
				r = session.get(ajax_url, headers=headers)
				r.raise_for_status()
				soup = BeautifulSoup(r.content, 'html.parser')
				page += 1

				if r.content == b'':
				
					break

				logging.info(ajax_url)
				countdown(2, 0, 2)
				logging.info(f'Status code: {r.status_code}')

				if m == 'photos' and not skip_photos:
					get_imgs_data(soup, meta_object, base_url)

				if m == 'videos' and not skip_videos:
					get_vids_data(soup, meta_object, base_url)

				if m == 'view' and not skip_posts:
					get_posts_data(soup, meta_object)

def get_posts_data(soup: BeautifulSoup, meta_object: MetaObject) -> None:
	posts_elements = soup.find_all(class_='post-text')

	if posts_elements:

		for ele in posts_elements:
			post_text = detect_text(ele)
			dynamic_id_parent = ele.find_parent('div', class_='huttPost')

			if dynamic_id_parent:
				dynamic_id = dynamic_id_parent.get('id').replace('post-', '')

				meta_object.posts.append(Post(id=dynamic_id, description=post_text))

def get_imgs_data(soup: BeautifulSoup, meta_object: MetaObject, base_url: str) -> None:
	carousels = soup.find_all('div', class_='carousel-inner')

	for carousel in carousels:
		parent_div = carousel.find_parent('div', id=lambda x: x and x.startswith('grid-carousel-'))

		if parent_div:
			dynamic_id = parent_div.get('id').replace('grid-carousel-', '')
			post_modal_div = parent_div.find_next_sibling(lambda x: x.name == 'div' and x.get('id', '').startswith('post-modal'))

			if post_modal_div:
				post_modal_body = post_modal_div.find('div', class_='modal-body')

				if post_modal_body:
					post_text_element = post_modal_body.find('div', class_='post-text')

					if post_text_element:
						post_text = detect_text(post_text_element)

		carousel_imgs = carousel.find_all('img')

		for idx, ele in enumerate(carousel_imgs):
			src = ele.get('src') or ele.get('data-src')

			if src:
				meta_object.photos.append(Photo(id=f'{dynamic_id}-{idx+1}', data=Info(url=f'{base_url}{src.replace("/middle", "")}', description=post_text)))

	img_elements = soup.find_all('img')

	for ele in img_elements:
		event_wrap_ele = ele.parent.find(class_='eventwrap')
	
		if event_wrap_ele:
			dynamic_id = event_wrap_ele.get('data-post-hash')

		src = ele.get('src') or ele.get('data-src')

		if src:
			modal_id = f'post-modal-{dynamic_id}'
			modal = soup.find('div', id=modal_id)

			if modal:
				post_text_element = modal.find('div', class_='post-text') #type: ignore

				if post_text_element:
					post_text = detect_text(post_text_element)
	
			if dynamic_id not in [p.id.split('-')[0] for p in meta_object.photos] and '/middle' in src:
				meta_object.photos.append(Photo(id=dynamic_id, data=Info(url=f'{base_url}{src.replace("/middle", "")}', description=post_text)))

def get_vids_data(soup: BeautifulSoup, meta_object: MetaObject, base_url: str) -> None:
	videos_elements = soup.find_all('video')

	if videos_elements:

		for ele in videos_elements:
			parent_ele = ele.find_parent('div', id=lambda x: x and x.startswith('post-modal'))

			if parent_ele:
				dynamic_id = parent_ele.get('id').replace('post-modal-', '')
				post_text_element = parent_ele.find(class_='post-text')

				if post_text_element:
					post_text = detect_text(post_text_element)

			src = f'{base_url}{ele.find("source").get("src")}'
			meta_object.videos.append(Video(id=dynamic_id, data=Info(url=src.replace('/middle', ''), description=post_text)))

def save_posts(meta_object: MetaObject, performer: str, config: dict[str, str]) -> None:
	posts_dict = {}
	output_path = os.path.join(config['save_path'], performer, f'{performer}.json')
	total = len(meta_object.posts)

	for idx, p in enumerate(meta_object.posts):
		logging.info(f'Saving post {idx+1} out of {total} with hash number: {p.id}')
		posts_dict[p.id] = p.description

	save_json(posts_dict, output_path)

def get_dl_img(meta_object: MetaObject, performer: str, config: dict[str, str], session: requests.sessions.Session, base_url: str) -> None:	
	total = len(meta_object.photos)

	for idx, p in enumerate(meta_object.photos):
		clean_pd = clean_string(p.data.description)[0:48].strip() if clean_string(p.data.description) else 'NA'
		item_no = idx+1
		logging.info(f'Downloading photo {item_no} out of {total} with hash: {p.id}')
		output_path = os.path.join(config['save_path'], performer, 'Images', f'{performer} - {p.id} - {clean_pd}.jpg')
		s = make_request(p.data.url, session, referer={'Referer': f'{base_url}/{performer}/photos'})

		with open(output_path, 'wb') as f: 
			f.write(s.content)

		countdown(2, item_no, total)

def get_dl_vids(meta_object: MetaObject, performer: str, config: dict[str, str], cookies_path: str, base_url: str) -> None:
	total = len(meta_object.videos)
 
	for idx, v in enumerate(meta_object.videos):
		clean_vd = clean_string(v.data.description)[0:48].strip() if clean_string(v.data.description) else 'NA'
		item_no = idx+1
		logging.info(f'Downloading video {item_no} out of {total}')

		yt_dlp_command = [
			'yt-dlp', v.data.url,
			'--abort-on-unavailable-fragments',
			'--hls-prefer-native',
			'--retries', '100',
			'--retry-sleep', '4',
			'--user-agent', user_agent,
			'--referer', f'{base_url}/{performer}/videos',
			'--cookies', cookies_path,
			'-o', os.path.normpath(os.path.join(config['save_path'], performer, 'Videos', f'{performer} - {v.id} - {clean_vd}.%(ext)s'))
		]

		subprocess.run(yt_dlp_command, check=False)
		countdown(4, item_no, total)

def get_id(soup: BeautifulSoup) -> int:
	id_element = soup.find('input', {'type': 'hidden', 'name': 'id'})

	if isinstance(id_element, Tag):
		id_value = id_element.get('value')

		if isinstance(id_value, str):

			return int(id_value)

	raise ValueError("id not found or is not a valid integer")

def get_last_segment(url: str) -> str:
	parsed_url = urlparse(url)

	return parsed_url.path.replace('/', '')

def main() -> None:
	parser = parse_huttpy()
	args = parser.parse_args(sys.argv[1:])
 
	for arg in args.url:
		logging.info(f'Processing: {arg}')

		try:
			config = load_toml()
			base_url = config['base_url']
			cookies_path = os.path.join(os.path.expanduser("~"), ".config", "huttpy", "huttpy_cookies.txt")
			session = load_session(cookies_path)
			r = make_request(arg, session, referer=None)
			r.raise_for_status
			soup = BeautifulSoup(r.content, 'html.parser')
			perf_id = get_id(soup)
			performer = get_last_segment(arg)
			meta_object = MetaObject(performer=performer)
			get_hutt(session, meta_object, perf_id, performer, base_url, args.skip_posts, args.skip_photos, args.skip_videos)
			print_json(data={'performer': performer, 'posts_count': len(meta_object.posts), 'photos_count': len(meta_object.photos), 'videos_count': len(meta_object.videos)}, indent=4)

			if args.json:
				filename = f'huttpy-Dict-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.json'

				if os.path.isfile(args.output):
					output = args.output

				elif os.path.isdir(args.output):

					if not os.path.exists(args.output):
						os.makedirs(args.output)

					output = os.path.join(args.output, filename)

				else:
					full_path = os.path.join(os.path.expanduser('~'), filename)
					logging.warning(f'Path does not exist, defaulting to: {full_path}')
					output = os.path.join(os.path.expanduser('~'), 'Desktop', filename)

				save_json(meta_object.asdict(), output)

			if not args.no_download:

				if not args.no_prompts:
					input('Press Enter to start downloading')

				if meta_object:
					make_dirs(config, performer, len(meta_object.photos), len(meta_object.videos))

				if meta_object.posts and not args.skip_posts:
					save_posts(meta_object, performer, config)

				if meta_object.photos and not args.skip_photos:
					get_dl_img(meta_object, performer, config, session, base_url)

				if meta_object.videos and not args.skip_videos:
					get_dl_vids(meta_object, performer, config, cookies_path, base_url)

		except (KeyError, FileNotFoundError, json.JSONDecodeError, requests.exceptions.ConnectionError, requests.exceptions.HTTPError, ValueError) as e:
			logging.error(f'{type(e).__name__}: {e}')
			sys.exit()

if __name__ == '__main__':
	main()