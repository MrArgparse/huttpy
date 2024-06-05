from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass, field
from datetime import datetime
from getuseragent import UserAgent #type: ignore
from http.cookiejar import MozillaCookieJar, LoadError
from rich.logging import RichHandler
from rich import print_json
from urllib.parse import urlparse, urljoin
from typing import cast, List, Optional, Union
import argparse
import json
import logging
import msgspec
import os
import pathlib
import platformdirs
import random
import requests
import subprocess
import sys
import time
import tomllib
import tomlkit
import types

DEFAULT_CHAR_TABLE = types.MappingProxyType({'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', 'À': 'A', 'È': 'E', 'Ì': 'I', 'Ò': 'O', 'Ù': 'U', 'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u', 'Â': 'A', 'Ê': 'E', 'Î': 'I', 'Ô': 'O', 'Û': 'U', 'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u', 'ÿ': 'y', 'Ä': 'A', 'Ë': 'E', 'Ï': 'I', 'Ö': 'O', 'Ü': 'U', 'Ÿ': 'Y', 'ã': 'a', 'Ã': 'A', 'ñ': 'n', 'Ñ': 'N', 'ç': 'c', 'Ç': 'C', 'ß': 'ss', 'æ': 'ae', 'Æ': 'AE', 'ø': 'o', 'Ø': 'O', 'œ': 'oe', 'Œ': 'OE', 'å': 'a', 'Å': 'A', 'ð': 'd', 'Ð': 'D', 'þ': 'th', 'Þ': 'TH', 'ý': 'y', 'Ý': 'Y', 'đ': 'd', 'Đ': 'D', 'ħ': 'h', 'Ħ': 'H', 'ı': 'i', 'İ': 'I', 'ł': 'l', 'Ł': 'L', 'ń': 'n', 'Ń': 'N', 'ŕ': 'r', 'Ŕ': 'R', 'ś': 's', 'Ś': 'S', 'ź': 'z', 'Ź': 'Z', 'ż': 'z', 'Ż': 'Z', 'š': 's', 'Š': 'S', 'č': 'c', 'Č': 'C', 'ř': 'r', 'Ř': 'R', 'ž': 'z', 'Ž': 'Z', 'ŭ': 'u', 'Ŭ': 'U', 'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S', 'ĉ': 'c', 'Ĉ': 'C', 'ĝ': 'g', 'Ĝ': 'G', 'ĥ': 'h', 'Ĥ': 'H', 'ĵ': 'j', 'Ĵ': 'J', 'ŝ': 's', 'Ŝ': 'S', 'ő': 'o', 'Ő': 'O', 'ű': 'u', 'Ű': 'U', 'ą': 'a', 'Ą': 'A', 'ę': 'e', 'Ę': 'E', 'ǫ': 'o', 'Ǫ': 'O', 'ų': 'u', 'Ų': 'U', 'ļ': 'l', 'Ļ': 'L', 'ņ': 'n', 'Ņ': 'N', 'ŗ': 'r', 'Ŗ': 'R', 'ķ': 'k', 'Ķ': 'K', 'ā': 'a', 'Ā': 'A', 'ē': 'e', 'Ē': 'E', 'ī': 'i', 'Ī': 'I', 'ū': 'u', 'Ū': 'U', 'ō': 'o', 'Ō': 'O', 'ȳ': 'y', 'Ȳ': 'Y', 'ə': 'e', 'Ə': 'E', '\'': ''})
USER_DIR = pathlib.Path.home()
PLATFORMDIRS = platformdirs.PlatformDirs(appname='huttpy', appauthor=False)
CONFIG_FOLDER = PLATFORMDIRS.user_config_path
DEFAULT_CONFIGURATION_PATH = CONFIG_FOLDER / 'huttpy_config.toml'
DEFAULT_SAVE_PATH = PLATFORMDIRS.user_downloads_path / 'huttpy'
COOKIES_PATH = CONFIG_FOLDER / 'huttpy_cookies.txt'
DEFAULT_ENCODING = 'utf-8'
logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
BROWSER_LIST = ['chrome', 'firefox']
BROWSER = random.choice(BROWSER_LIST)
USER_AGENT = UserAgent('chrome', limit=1).list[0]

class DefaultConfig(msgspec.Struct, kw_only=True):
	base_url: str = 'https://hutt.co'
	save_path: str = os.fspath(DEFAULT_SAVE_PATH)
	filename_format: str = '{username} - {post_id} - {text_cleaned}'
	char_limit: int = 48
	lowercase: bool = False
	char_table: dict[str, str] = msgspec.field(default_factory=DEFAULT_CHAR_TABLE.copy)

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
	performer_id: int
	posts: List[Post] = field(default_factory=list)
	photos: List[Photo] = field(default_factory=list)
	videos: List[Video] = field(default_factory=list)

	def asdict(self) -> dict[str, str | object]:
		return {
			"performer": self.performer,
			"performer_id": self.performer_id,
			"posts": {post.id: post.description for post in self.posts},
			"photos": {photo.id: photo.data.__dict__ for photo in self.photos},
			"videos": {video.id: video.data.__dict__ for video in self.videos}
		}

def parse_huttpy() -> argparse.ArgumentParser:
	parser=argparse.ArgumentParser(prog='huttpy')
	parser.add_argument('url', nargs='+', help='url')
	parser.add_argument('--json', '-j', action='store_true', default=False, help='Outputs to a json file')
	parser.add_argument('--load-dict', '-l', action='store_true', default=False, help='Load previously scraped json, will treat positional argument as a json filepath.')
	parser.add_argument('--no-download', '-n', action='store_true', default=False, help='Scrapes information without downloading')
	parser.add_argument('--no-prompts', '-p', action='store_true', default=False, help='Does not prompt before downloading.')
	parser.add_argument('--skip-posts', '-s', action='store_true', default=False, help='Skips downloading/scraping the posts.')
	parser.add_argument('--skip-photos', '-t', action='store_true', default=False, help='Skips downloading/scraping the photos.')
	parser.add_argument('--skip-videos', '-v', action='store_true', default=False, help='Skips downloading/scraping the videos.')
	parser.add_argument('--output', '-o', default=os.path.join(os.path.expanduser('~'), 'Desktop', f'Hutt-Dict-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.json'), help='Specify output path for the metadata only (Defaults to Desktop). Use config for download path.')

	return parser

def load_toml(config_file: str) -> dict[str, str]:

	with open(config_file, 'rb') as f:
		toml_dict = tomllib.load(f)

	return toml_dict

def save_toml(toml_dict: dict[str, str], toml_path: str) -> None:

	with open(toml_path, 'w') as c:
		c.write(tomlkit.dumps(toml_dict))

def save_json(content: dict[str, object] | dict[str, str], path: str, indent: int = 4) -> None:

	with open(path, 'w', encoding='utf8') as json_file:
		json.dump(content, json_file, indent=indent)

def get_config_path(path: Union[str, os.PathLike[str], None] = None) -> pathlib.Path:
	if path is None:
		return DEFAULT_CONFIGURATION_PATH

	return pathlib.Path(os.path.normpath(os.path.abspath(path)))

def load_config(path: Union[str, os.PathLike[str], None] = None) -> DefaultConfig:
	path = get_config_path(path)

	with open(path, 'r', encoding=DEFAULT_ENCODING) as fp:
		data = fp.read()

	config_dict = tomlkit.loads(data)

	return msgspec.convert(config_dict, type=DefaultConfig)

def save_config(configuration: DefaultConfig, path: Union[str, os.PathLike[str], None] = None) -> None:
	path = get_config_path(path)

	data = tomlkit.dumps(msgspec.to_builtins(configuration))

	path.parent.mkdir(parents=True, exist_ok=True)
	with open(path, 'w', encoding=DEFAULT_ENCODING) as fp:
		fp.write(data)

	logging.info(f'New default config saved in: {DEFAULT_CONFIGURATION_PATH}')

def load_or_create_config(path: Union[str, os.PathLike[str], None] = None) -> DefaultConfig:
	path = get_config_path(path)

	if path is not None:
		logging.info(f'Previous config found in: {DEFAULT_CONFIGURATION_PATH}')

	try:
		return load_config(path)

	except FileNotFoundError:
		pass

	configuration = DefaultConfig()
	save_config(configuration, path)
	return configuration

CONFIG = load_or_create_config()
BASE_URL = CONFIG.base_url
CHAR_TABLE = CONFIG.char_table
TABLE = str.maketrans(CHAR_TABLE)

def load_session() -> requests.sessions.Session:
	cookie_jar = MozillaCookieJar(COOKIES_PATH)
	cookie_jar.load(ignore_discard=True, ignore_expires=True)
	session = requests.Session()
	session.cookies = cast(requests.cookies.RequestsCookieJar, cookie_jar)

	return session

try:
	SESSION = load_session()

except FileNotFoundError:
	logging.error(f'Cookies missing from: {str(COOKIES_PATH)}')
	sys.exit(1)

except LoadError:
	logging.error(f'Invalid Netscape cookies file: {str(COOKIES_PATH)}')
	sys.exit(1)

finally:
	logging.info(f'Previous cookies found in: {str(COOKIES_PATH)}')

def make_request(url: str, referer: Optional[dict[str, str]]) -> requests.Response:
	headers = {'User-Agent': USER_AGENT}

	if referer:
		headers.update(referer)

	return SESSION.get(url, headers=headers)

def countdown(seconds: int, idx: int, total: int) -> None:

	if idx != total:

		while seconds > 0:
			time.sleep(1)
			seconds -= 1

def make_dirs(performer: str, photos_count: int, videos_count: int) -> None:

	if photos_count:
		directory1 = os.path.join(CONFIG.save_path, performer, 'Images')
		os.makedirs(directory1, exist_ok=True)

	if videos_count:
		directory2 = os.path.join(CONFIG.save_path, performer, 'Videos')
		os.makedirs(directory2, exist_ok=True)

def format_filenames(performer: str, post_id: str, text: str) -> str:
	filename_format = CONFIG.filename_format
	char_limit = int(CONFIG.char_limit)
	clean_text = clean_string(text)[0:char_limit].strip()

	if CONFIG.lowercase == False:
		clean_text = clean_text.lower()

	format_dict: dict[str, object] = {
		'username': performer,
		'post_id': post_id,
		'text': text,
		'text_cleaned': clean_text if clean_text else 'NA',
	}

	return str(filename_format.format(**format_dict))

def clean_string(string: str) -> str:
	intermediate_string1 = string.translate(TABLE)
	intermediate_string2 = intermediate_string1.translate({ord(c): ' ' for c in intermediate_string1 if not c.isalnum()})

	return ' '.join(intermediate_string2.split())

def detect_text(element: Tag) -> str:

	post_text = element.text if hasattr(element, 'text') else ''
		
	return post_text

def get_local_hutt(content_path: str) -> MetaObject:

	with open(content_path, 'r', encoding='utf8') as json_file:
		content = json.load(json_file)

	meta_object = MetaObject(performer=content['performer'], performer_id=int(content['performer_id']))

	if 'photos' in content:

		for k in content['photos'].keys():
			meta_object.photos.append(Photo(id=k, data=Info(url=content['photos'][k]['url'], description=content['photos'][k]['description'])))

	if 'posts' in content:

		for k in content['posts'].keys():
			meta_object.posts.append(Post(id=k, description=content['posts'][k]))

	if 'videos' in content:

		for k in content['videos'].keys():
			meta_object.videos.append(Video(id=k, data=Info(url=content['videos'][k]['url'], description=content['videos'][k]['description'])))

	return meta_object

def get_hutt(meta_object: MetaObject, perf_id: int,  performer: str, base_url: str, skip_posts: bool = False, skip_photos: bool = False, skip_videos: bool = False) -> None:	
	media_types = ['photos', 'videos', 'view']
	headers = {'Referer': urljoin(base_url, performer), 'User-Agent': USER_AGENT}

	for m in media_types:
		page = 0

		if (m == 'view' and not skip_posts) or (m == 'photos' and not skip_photos) or (m == 'videos' and not skip_videos):

			if m in ['photos', 'videos']:
				headers['Referer'] = f'{headers["Referer"]}{m}'

			while True:
				ajax_url = f'{BASE_URL}/hutts/ajax-posts?page={page}&view={m}&id={perf_id}'
				r = SESSION.get(ajax_url, headers=headers)
				r.raise_for_status()
				soup = BeautifulSoup(r.content, 'html.parser')
				page += 1
				seconds = 2

				if r.content == b'':
				
					break

				logging.info(f'{ajax_url} - Status code: {r.status_code} - Sleeping: {seconds} seconds')
				countdown(seconds, 0, 2)

				if m == 'photos' and not skip_photos:
					get_imgs_data(soup, meta_object)

				if m == 'videos' and not skip_videos:
					get_vids_data(soup, meta_object)

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

def get_imgs_data(soup: BeautifulSoup, meta_object: MetaObject) -> None:
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
				meta_object.photos.append(Photo(id=f'{dynamic_id}-{idx+1}', data=Info(url=f'{BASE_URL}{src.replace("/middle", "")}', description=post_text)))

	img_elements = soup.find_all('img')

	for ele in img_elements:
		event_wrap_ele = ele.parent.find(class_='eventwrap')
	
		if event_wrap_ele:
			dynamic_id = event_wrap_ele.get('data-post-hash')

		src = ele.get('src') or ele.get('data-src')

		if src:
			modal_id = f'post-modal-{dynamic_id}'
			modal = soup.find('div', id=modal_id)

			if isinstance(modal, Tag):
				post_text_element = modal.find('div', class_='post-text') 

				if post_text_element:
					post_text = detect_text(post_text_element)
	
			if dynamic_id not in [p.id.split('-')[0] for p in meta_object.photos] and '/middle' in src:
				meta_object.photos.append(Photo(id=dynamic_id, data=Info(url=f'{BASE_URL}{src.replace("/middle", "")}', description=post_text)))

def get_vids_data(soup: BeautifulSoup, meta_object: MetaObject) -> None:
	videos_elements = soup.find_all('video')

	if videos_elements:

		for ele in videos_elements:
			parent_ele = ele.find_parent('div', id=lambda x: x and x.startswith('post-modal'))

			if parent_ele:
				dynamic_id = parent_ele.get('id').replace('post-modal-', '')
				post_text_element = parent_ele.find(class_='post-text')

				if post_text_element:
					post_text = detect_text(post_text_element)

			src = f'{BASE_URL}{ele.find("source").get("src")}'
			meta_object.videos.append(Video(id=dynamic_id, data=Info(url=src.replace('/middle', ''), description=post_text)))

def save_posts(meta_object: MetaObject, performer: str) -> None:
	posts_dict = {}
	output_path = os.path.join(CONFIG.save_path, performer, f'{performer}.json')
	total = len(meta_object.posts)

	for idx, p in enumerate(meta_object.posts):
		logging.info(f'Saving post {idx+1} out of {total} with hash number: {p.id}')
		posts_dict[p.id] = p.description

	save_json(posts_dict, output_path)

def get_dl_img(meta_object: MetaObject, performer: str, skip_videos: bool) -> None:
	total = len(meta_object.photos)
	max_retries = 4

	for idx, p in enumerate(meta_object.photos):
		item_no = idx + 1
		seconds: int = 2
		logging.info(f'Downloading photo {item_no} out of {total} with hash: {p.id}')
		fname = format_filenames(performer, p.id, p.data.description)
		output_path = os.path.join(CONFIG.save_path, performer, 'Images', f'{fname}.jpg')
		
		for attempt in range(max_retries):

			try:
				s = make_request(p.data.url, referer={'Referer': f'{BASE_URL}/{performer}/photos'})

				with open(output_path, 'wb') as f:
					f.write(s.content)

				break

			except requests.exceptions.RequestException as e:
				logging.warning(f'Attempt {attempt + 1} failed for photo {p.id}: {e}')
				retry_seconds = 4
				logging.info(f'Seeping: {seconds} seconds')

				if attempt < max_retries - 1:
					countdown(retry_seconds, 0, 4)

				else:
					logging.error(f'Failed to download photo {p.id} after {max_retries} attempts')

		if item_no == total and skip_videos:

			return

		logging.info(f'Sleeping: {seconds} seconds')
		countdown(seconds, item_no, total)

def get_dl_vids(meta_object: MetaObject, performer: str) -> None:
	total = len(meta_object.videos)
 
	for idx, v in enumerate(meta_object.videos):
		fname = format_filenames(performer, v.id, v.data.description)
		item_no = idx+1
		seconds = 4 
		logging.info(f'Downloading video {item_no} out of {total}')

		yt_dlp_command = [
			'yt-dlp', v.data.url,
			'--abort-on-unavailable-fragments',
			'--hls-prefer-native',
			'--retries', '100',
			'--retry-sleep', '4',
			'--user-agent', USER_AGENT,
			'--referer', f'{BASE_URL}/{performer}/videos',
			'--cookies', str(COOKIES_PATH),
			'-o', os.path.normpath(os.path.join(CONFIG.save_path, performer, 'Videos', f'{fname}.%(ext)s'))
		]

		subprocess.run(yt_dlp_command, check=False)

		if item_no != total:
			logging.info(f'Sleeping: {seconds} seconds')
			countdown(seconds, item_no, total)

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

def test_cookies(soup: BeautifulSoup) -> bool:
	sign_up = soup.find(class_='sign-up')
	have_account = soup.find(class_='have-account') 

	if sign_up or have_account:
		return True

	return False

def main() -> None:
	parser = parse_huttpy()
	args = parser.parse_args(sys.argv[1:])
 
	for arg in args.url:
		logging.info(f'Processing: {arg}')

		try:

			if args.load_dict:
				meta_object = get_local_hutt(arg)
				performer, perf_id = meta_object.performer, meta_object.performer_id

			if not args.load_dict:
				r = make_request(arg, referer=None)
				r.raise_for_status
				soup = BeautifulSoup(r.content, 'html.parser')
				bad_cookies = test_cookies(soup)
					
				if bad_cookies:
					logging.error('Cannot log in: Cookies expired or invalid.')
					logging.info(f'Location of cookies file: {COOKIES_PATH}')
					sys.exit(1)

				perf_id = get_id(soup)
				performer = get_last_segment(arg)
				meta_object = MetaObject(performer=performer, performer_id=perf_id)
				get_hutt(meta_object, perf_id, performer, args.skip_posts, args.skip_photos, args.skip_videos)

			print_json(data={'performer': performer, 'performer_id': perf_id, 'posts_count': len(meta_object.posts), 'photos_count': len(meta_object.photos), 'videos_count': len(meta_object.videos)}, indent=4)

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
					make_dirs(performer, len(meta_object.photos), len(meta_object.videos))

				if meta_object.posts and not args.skip_posts:
					save_posts(meta_object, performer)

				if meta_object.photos and not args.skip_photos:
					get_dl_img(meta_object, performer, args.skip_videos)

				if meta_object.videos and not args.skip_videos:
					get_dl_vids(meta_object, performer)

		except (KeyError, FileNotFoundError, json.JSONDecodeError, requests.exceptions.ConnectionError, requests.exceptions.HTTPError, ValueError) as e:
			logging.error(f'{type(e).__name__}: {e}')
			sys.exit()

if __name__ == '__main__':
	main()