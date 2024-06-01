from bs4 import BeautifulSoup, Tag
from dataclasses import asdict, dataclass, field
from datetime import datetime
from getuseragent import UserAgent #type: ignore
from http.cookiejar import MozillaCookieJar
from rich.logging import RichHandler
from rich import print_json
from urllib.parse import urlparse
from typing import cast, Optional
import http.cookiejar as cookiejar
import argparse
import json
import logging
import os
import random
import re
import requests
import subprocess
import sys
import time
import tomllib
import tomlkit

@dataclass(kw_only=True)
class DefaultConfig:
	BaseUrl: str = 'https://hutt.co'
	SavePath: str = os.path.expanduser('~')

@dataclass(kw_only=True)
class MetaObject:
	Performer: str
	Posts: list[str] = field(default_factory=list)
	PostsHashes: list[str] = field(default_factory=list)
	Photos: list[str] = field(default_factory=list)
	PhotosHashes: list[str] = field(default_factory=list)
	Videos: list[str] = field(default_factory=list)
	VideosDescriptions: list[str] = field(default_factory=list)
	VideosHashes: list[str] = field(default_factory=list)

def load_toml() -> dict[str, str]:
	config_path: str = os.path.join(os.path.expanduser("~"), ".config", "huttpy")
	config_file = os.path.join(config_path, 'huttpy_config.toml')

	with open(config_file, 'rb') as f:
		toml_dict = tomllib.load(f)

	return toml_dict

def parse_huttpy() -> argparse.ArgumentParser:
	parser=argparse.ArgumentParser(prog='huttpy')
	parser.add_argument('url', nargs='+', help='URL')
	parser.add_argument('--json', '-j', action='store_true', default=False, help='Outputs to a json file')
	parser.add_argument('--no-download', '-n', action='store_true', default=False, help='Scrapes information without downloading')
	parser.add_argument('--no-prompts', '-p', action='store_true', default=False, help='Does not prompt before downloading.')
	parser.add_argument('--skip-posts', '-s', action='store_true', default=False, help='Skips downloading/scraping the posts.')
	parser.add_argument('--skip-photos', '-t', action='store_true', default=False, help='Skips downloading/scraping the photos.')
	parser.add_argument('--skip-videos', '-v', action='store_true', default=False, help='Skips downloading/scraping the videos.')
	parser.add_argument('--output', '-o', default=os.path.join(os.path.expanduser('~'), 'Desktop', f'Hutt-Dict-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.json'), help='Specify output path for the metadata only (Defaults to Desktop). Use config for download path.')

	return parser

def save_json(content: dict[str, MetaObject] | dict[str, str], path: str, indent: int = 4) -> None:

	with open(path, 'w', encoding='utf8') as json_file:
		json.dump(content, json_file, indent=indent)

def get_agent() -> str:
	browser_list = ['chrome', 'firefox']
	browser = random.choice(browser_list)
	user_agent = str(UserAgent(browser, limit=1).list[0])

	return user_agent

def make_request(url: str, session: requests.sessions.Session, referer: Optional[dict[str, str]]) -> requests.Response:
	user_agent = get_agent()
	headers = {'User-Agent': user_agent}

	if referer:
		headers.update(referer)

	r = session.get(url, headers=headers)

	return r

def clean_string(string: str) -> str:
	accents_dict = {
		'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
		'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
		'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
		'À': 'A', 'È': 'E', 'Ì': 'I', 'Ò': 'O', 'Ù': 'U',
		'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u',
		'Â': 'A', 'Ê': 'E', 'Î': 'I', 'Ô': 'O', 'Û': 'U',
		'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u', 'ÿ': 'y',
		'Ä': 'A', 'Ë': 'E', 'Ï': 'I', 'Ö': 'O', 'Ü': 'U', 'Ÿ': 'Y',
		'ñ': 'n', 'Ñ': 'N',
		'ç': 'c', 'Ç': 'C',
		'ß': 'ss',
		'æ': 'ae', 'Æ': 'AE',
		'ø': 'o', 'Ø': 'O',
		'œ': 'oe', 'Œ': 'OE'
	}

	pattern = re.compile('|'.join(accents_dict.keys()))
	intermediate_string1 = pattern.sub(lambda x: accents_dict[x.group()], string)
	intermediate_string2 = re.sub(r'[^A-Za-z0-9\s]', '', intermediate_string1)
	cleaned_string = re.sub(r'\s+', ' ', intermediate_string2).strip()

	return cleaned_string

def make_dirs(config: dict[str, str], performer: str, photos_count: int, videos_count: int) -> None:

	if photos_count:
		directory1 = os.path.join(config['SavePath'], performer, 'Images')
		os.makedirs(directory1, exist_ok=True)

	if videos_count:
		directory2 = os.path.join(config['SavePath'], performer, 'Videos')
		os.makedirs(directory2, exist_ok=True)

def save_posts(performer: str, posts: list[str], posts_hashes: list[str], config: dict[str, str]) -> None:
	logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])

	if posts:
		posts_dict = {}
		output_path = os.path.join(config['SavePath'], performer, f'{performer}.json')

		for p, ph in zip(posts, posts_hashes):
			logging.info(f'Saving post with hash number: {ph}')
			posts_dict[ph] = p

		save_json(posts_dict, output_path)

def get_dl_img(hrefs: list[str], performer: str, photos_hashes: list[str], config: dict[str, str], session: requests.sessions.Session) -> None:
	logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
	idx = 0
	total = len(hrefs)

	for hr, ph in zip(hrefs, photos_hashes):
		logging.info(f'Downloading photo {idx} out of {total} with hash: {ph}')
		idx = idx +1
		output_path = os.path.join(config['SavePath'], performer, 'Images', f'{performer} - {ph}.jpg')
		s = make_request(hr, session, referer={'Referer': 'https://hutt.co/GreatMoonGirl/photos'})

		with open(output_path, 'wb') as f: 
			f.write(s.content)

		if idx != total:
			logging.info('Sleeping for 2 seconds...')
			time.sleep(2)

def get_dl_vids(hrefs: list[str], performer: str, videos_descriptions: list[str], videos_hashes: list[str], config: dict[str, str], cookies_path: str) -> None:
	user_agent = get_agent()
	idx = 0
	total = len(hrefs)
 
	for hr, vd, vh in zip(hrefs, videos_descriptions, videos_hashes):
		clean_vd = clean_string(vd)[0:48].strip()

		if not clean_vd:
			clean_vd = 'NA'

		logging.info(f'Downloading video {idx} out of {total}')
		idx = idx +1

		yt_dlp_command = [
			'yt-dlp', hr,
			'--abort-on-unavailable-fragments',
			'--hls-prefer-native',
			'--retries', '100',
			'--retry-sleep', '4',
			'--user-agent', user_agent,
			'--referer', f'https://hutt.co/{performer}/videos',
			'--cookies', cookies_path,
			'-o', os.path.normpath(os.path.join(config['SavePath'], performer, 'Videos', f'{performer} - {vh} - {clean_vd}.%(ext)s'))
		]

		subprocess.run(yt_dlp_command, check=False)

		if idx != total:
			logging.info('Sleeping for 8 seconds...')
			time.sleep(8)

def get_hutt(session: requests.sessions.Session, perf_id: int,  performer: str, skip_posts: bool = False, skip_photos: bool = False, skip_videos: bool = False) -> MetaObject:
	logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
	media_types = ['photos', 'videos', 'view']
	user_agent = get_agent()
	posts = []
	posts_hashes = []
	photos = []
	photos_hashes = []
	videos = []
	videos_descriptions = []
	videos_hashes = []
	headers = {'Referer': f'https://hutt.co/{performer}/', 'User-Agent': user_agent}

	for m in media_types:
		page = 0

		if (m == 'view' and not skip_posts) or (m == 'photos' and not skip_photos) or (m == 'videos' and not skip_videos):

			if m in ['photos', 'videos']:
				headers['Referer'] = f'{headers["Referer"]}{m}'

			while True:
				ajax_url = f'https://hutt.co/hutts/ajax-posts?page={page}&view={m}&id={perf_id}'
				logging.info(ajax_url)
				r = session.get(ajax_url, headers=headers)
				r.raise_for_status()
				soup = BeautifulSoup(r.content, 'html.parser')
				page = page + 1
				logging.info(f'Status code: {r.status_code}')

				if r.content == b'':
				
					break

				if m == 'photos' and not skip_photos:
					photos_elements = soup.find_all('img')

					if photos_elements:
						filtered_photos_elements = [fpe for fpe in photos_elements if fpe.get('src') != None and '/middle' in fpe.get('src')]
						filtered_photos_hrefs = [f'https://hutt.co{fph.get("src")}' for fph in filtered_photos_elements]
						photos.extend(filtered_photos_hrefs)
						photos_hashes.extend([urlparse(f).path.split('/')[2].split('-')[0] for f in filtered_photos_hrefs])
						logging.info('Sleeping for 2 seconds...')
						time.sleep(2)

				if m == 'videos' and not skip_videos:
					videos_elements = soup.find_all('video')

					if videos_elements:
						videos.extend([f'https://hutt.co{ele.find("source").get("src")}' for ele in videos_elements])
						videos_descriptions.extend([ele.text for ele in soup.find_all(class_='post-text')])
						videos_hashes.extend([ele.get('data-id') for ele in soup.find_all('figure', class_='hutt-video')])
						logging.info('Sleeping for 2 seconds...')
						time.sleep(2)

				if m == 'view' and not skip_posts:
					posts_elements = soup.find_all(class_='post-text')

					if posts_elements:
						posts.extend([ele.text for ele in soup.find_all(class_='post-text')])
						posts_hashes.extend([pe.find_parent('div', class_='huttPost')['id'].strip('-post') for pe in posts_elements if 'id' in pe.find_parent('div', class_='huttPost').attrs])
						logging.info('Sleeping for 2 seconds...')
						time.sleep(2)

	meta_object = MetaObject(
		Performer = performer,
		Posts = posts,
		PostsHashes = posts_hashes,
		Photos = photos,
		PhotosHashes = photos_hashes,
		Videos = videos,
		VideosDescriptions = videos_descriptions,
		VideosHashes = videos_hashes
	)

	return meta_object

def get_id(soup: BeautifulSoup) -> int:
	id_element = soup.find('input', {'type': 'hidden', 'name': 'id'})

	if isinstance(id_element, Tag):
		id_value = id_element.get('value')

		if isinstance(id_value, str):

			return int(id_value)

	raise ValueError("ID not found or is not a valid integer")

def get_last_segment(url: str) -> str:
	parsed_url = urlparse(url)
	path = parsed_url.path.replace('/', '')

	return path

def load_json(path: str) -> dict[str, str|list[str]]:

	with open(path, 'r', encoding='utf8') as json_file:
		
		return cast(dict[str, str|list[str]], json_file)

def load_session(cookies_path: str) -> requests.sessions.Session:
	cookie_jar = MozillaCookieJar(cookies_path)
	cookie_jar.load(ignore_discard=True, ignore_expires=True)
	session = requests.Session()
	session.cookies = cookie_jar #type: ignore

	return session

def load_huttpy_config() -> dict[str, str]:
	default_config = DefaultConfig()
	config_path = os.path.join(os.path.expanduser("~"), ".config", "huttpy")
	config_file = os.path.join(config_path, 'huttpy_config.toml')

	if not os.path.isfile(config_file):
		os.makedirs(config_path, exist_ok=True)
		save_toml(asdict(default_config), config_file)

	conf = load_toml(config_file)

	return conf

def save_toml(toml_dict: dict[str, str], toml_path: str) -> None:

	with open(toml_path, 'w') as c:
		c.write(tomlkit.dumps(toml_dict))

def main() -> None:
	logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
	parser = parse_huttpy()
	args = parser.parse_args(sys.argv[1:])

	for arg in args.url:
		logging.info(f'Processing: {arg}')

		try:
			config = load_toml()
			cookies_path = os.path.join(os.path.expanduser("~"), ".config", "huttpy", "huttpy_cookies.txt")
			session = load_session(cookies_path)
			r = make_request(arg, session, referer=None)
			r.raise_for_status
			soup = BeautifulSoup(r.content, 'html.parser')
			perf_id = get_id(soup)
			performer = get_last_segment(arg)
			metadata = get_hutt(session, perf_id, performer, args.skip_posts, args.skip_photos, args.skip_videos)
			print_json(data={'Performer': performer, 'PostsCount': len(metadata.Posts), 'PhotosCount': len(metadata.Photos), 'VideosCount': len(metadata.Videos)}, indent=4)

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

				save_json(asdict(metadata), output)

			if not args.no_prompts:
				input('Press Enter to start downloading')

			if not args.no_download:

				if metadata:
					make_dirs(config, performer, len(metadata.Photos), len(metadata.Videos))

				if metadata.Posts and not args.skip_posts:
					save_posts(performer, metadata.Posts, metadata.PostsHashes, config)

				if metadata.Photos and not args.skip_photos:
					get_dl_img(metadata.Photos, performer, metadata.PhotosHashes, config, session)

				if metadata.Videos and not args.skip_videos:
					get_dl_vids(metadata.Videos, performer, metadata.VideosDescriptions, metadata.VideosHashes, config, cookies_path)

		except (KeyError, FileNotFoundError, json.JSONDecodeError, requests.exceptions.ConnectionError, requests.exceptions.HTTPError, ValueError) as e:
			logging.error(f'{type(e).__name__}: {e}')
			sys.exit()

if __name__ == '__main__':
	main()