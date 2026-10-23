"""
End-to-end test of the test app: real runserver, real Chromium browser and real Cloudinary account.
Cloudinary credentials are read from .env file in the project root, all uploaded files are removed at the end.

Usage:
    uv run --group e2e playwright install chromium  # only once
    uv run --group e2e python tests/e2e/run_e2e.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import cloudinary
import cloudinary.api
import requests
from playwright.sync_api import sync_playwright

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_PY = sys.executable
PORT = 8765
BASE = 'http://127.0.0.1:{}'.format(PORT)

E2E_DIR = tempfile.mkdtemp(prefix='dcs-e2e-')
EXTRA_STATIC = os.path.join(E2E_DIR, 'extra-static', 'e2e')
os.makedirs(EXTRA_STATIC)

ENV = dict(os.environ)
with open(os.path.join(REPO, '.env')) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            ENV[key] = value
ENV.update(DJANGO_SETTINGS_MODULE='tests.e2e_settings', E2E_DIR=E2E_DIR, E2E_EXTRA_STYLESHEET='e2e/theme.css',
           PYTHONUNBUFFERED='1')
CLOUD = ENV['CLOUDINARY_CLOUD_NAME']
cloudinary.config(cloud_name=CLOUD, api_key=ENV['CLOUDINARY_API_KEY'], api_secret=ENV['CLOUDINARY_API_SECRET'])

GREEN = 'rgb(0, 128, 0)'
RED = 'rgb(255, 0, 0)'
BLUE = 'rgb(0, 0, 255)'
THEME_V1 = "h1 { color: rgb(255, 0, 0); }\nh2 { background-image: url('../tests/images/dummy-static-image.jpg'); }\n"
THEME_V2 = THEME_V1.replace('rgb(255, 0, 0)', 'rgb(0, 0, 255)')

results = []
FILES_COUNT = None


def check(name, condition, detail=''):
    results.append((name, bool(condition), detail))
    print('{} {}{}'.format('PASS' if condition else 'FAIL', name, ' -- ' + str(detail) if detail else ''), flush=True)
    return condition


def manage(*args, env=None, ok=True):
    run_env = dict(ENV, **(env or {}))
    proc = subprocess.run([APP_PY, 'manage.py'] + list(args), cwd=REPO, env=run_env, capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    if ok and proc.returncode != 0:
        raise RuntimeError('manage.py {} failed:\n{}'.format(' '.join(args), output))
    return output


class Server(object):
    def __init__(self, **env):
        self.env = env

    def __enter__(self):
        run_env = dict(ENV, **self.env)
        self.log = open(os.path.join(E2E_DIR, 'server.log'), 'a')
        self.proc = subprocess.Popen([APP_PY, 'manage.py', 'runserver', '127.0.0.1:{}'.format(PORT), '--noreload'],
                                     cwd=REPO, env=run_env, stdout=self.log, stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                requests.get(BASE + '/', timeout=1)
                return self
            except requests.ConnectionError:
                time.sleep(0.2)
        raise RuntimeError('server did not start')

    def __exit__(self, *exc):
        self.proc.terminate()
        self.proc.wait()
        self.log.close()


def write_theme(content):
    with open(os.path.join(EXTRA_STATIC, 'theme.css'), 'w') as f:
        f.write(content)


def uploaded_count(output):
    match = re.search(r'(\d+) static files uploaded to Cloudinary, (\d+) unmodified', output)
    return (int(match.group(1)), int(match.group(2))) if match else None


def resource_exists(public_id, resource_type):
    try:
        cloudinary.api.resource(public_id, resource_type=resource_type)
        return True
    except cloudinary.exceptions.NotFound:
        return False


def load(page, path):
    """Opens a page and returns list of failed responses."""
    failures = []
    page.on('response', lambda r: failures.append((r.status, r.url)) if r.status >= 400 else None)
    page.on('requestfailed', lambda r: failures.append(('failed', r.url)))
    page.goto(BASE + path, wait_until='networkidle')
    return failures


def img_size(page, selector):
    return page.eval_on_selector(selector, 'img => img.complete ? [img.naturalWidth, img.naturalHeight] : null')


def css(page, selector, prop):
    return page.eval_on_selector(selector, 'el => getComputedStyle(el).getPropertyValue("{}")'.format(prop))


def static_hrefs(page):
    return page.eval_on_selector_all('link[rel=stylesheet], img', 'els => els.map(e => e.href || e.src)')


def scenario_hashed_static_and_media(browser):
    print('\n== Hashed static storage + media, DEBUG=False', flush=True)
    write_theme(THEME_V1)
    manage('migrate', '--noinput')
    output = manage('collectstatic', '--noinput')
    manifest_path = os.path.join(E2E_DIR, 'manifest', 'staticfiles.json')
    check('manifest saved in STATICFILES_MANIFEST_ROOT', os.path.exists(manifest_path))
    with open(manifest_path) as f:
        manifest = json.load(f)['paths']
    global FILES_COUNT
    FILES_COUNT = len(manifest)
    check('collectstatic uploads all {} hashed files'.format(FILES_COUNT), uploaded_count(output) == (FILES_COUNT, 0),
          uploaded_count(output))

    with Server():
        page = browser.new_page()
        failures = load(page, '/')
        check('index: no failed requests', not failures, failures)
        check('index: CSS from Cloudinary applied (green background)', css(page, 'body', 'background-color') == GREEN)
        size = img_size(page, 'img[alt="dummy static image"]')
        check('index: static image loaded', size and size[0] > 0, size)
        check('index: cloudinary_static transformed image is 50x50',
              img_size(page, 'img[src*="w_50"]') == [50, 50], img_size(page, 'img[src*="w_50"]'))
        hrefs = static_hrefs(page)
        check('index: all static urls point to Cloudinary under e2e-static with hashes',
              all('res.cloudinary.com' in h and '/e2e-static/' in h and re.search(r'\.[0-9a-f]{12}(\.|$)', h)
                  for h in hrefs), hrefs)
        page.close()

        page = browser.new_page()
        failures = load(page, '/uploads/')
        check('uploads: theme CSS v1 applied (red h1)', css(page, 'h1', 'color') == RED)
        css_image_failures = [f for f in failures if 'dummy-static-image' in f[1]]
        check('uploads: image referenced from CSS url() loads', not css_image_failures, css_image_failures)
        unexpected = [f for f in failures if 'dummy-static-image' not in f[1]]
        check('uploads: no other failed requests', not unexpected, unexpected)

        raw_path = os.path.join(E2E_DIR, 'e2e-raw.txt')
        with open(raw_path, 'w') as f:
            f.write('raw file content from e2e')
        page.fill('#id_image-name', 'e2e-image')
        page.set_input_files('#id_image-file', raw_path)
        page.set_input_files('#id_image-image', os.path.join(REPO, 'tests', 'dummy-files', 'dummy-image.jpg'))
        page.click('#image-form button')
        page.wait_for_load_state('networkidle')
        item = '.image-model[data-name="e2e-image"]'
        check('media: image form saved', page.locator(item).count() == 1)
        size = img_size(page, item + ' img.original-image')
        check('media: uploaded image loads from Cloudinary', size and size[0] > 0, size)
        check('media: {% cloudinary %} transformed image is 100x100',
              img_size(page, item + ' img.transformed-image') == [100, 100],
              img_size(page, item + ' img.transformed-image'))
        raw_url = page.get_attribute(item + ' a.raw-file', 'href')
        response = requests.get(raw_url)
        check('media: raw file downloadable with the same content',
              response.status_code == 200 and response.text == 'raw file content from e2e', raw_url)

        page.fill('#id_video-name', 'e2e-video')
        page.set_input_files('#id_video-video', os.path.join(REPO, 'tests', 'dummy-files', 'dummy-video.mp4'))
        page.click('#video-form button')
        page.wait_for_load_state('networkidle')
        video = '.video-model[data-name="e2e-video"] video'
        check('media: video form saved', page.locator(video).count() == 1)
        page.wait_for_function('v => v.readyState >= 1', arg=page.query_selector(video), timeout=20000)
        duration = page.eval_on_selector(video, 'v => v.duration')
        check('media: uploaded video plays in browser (metadata loaded)', duration and duration > 0, duration)

        fake_video = os.path.join(E2E_DIR, 'fake.mp4')
        with open(fake_video, 'w') as f:
            f.write('this is not a video')
        page.fill('#id_video-name', 'e2e-fake-video')
        page.set_input_files('#id_video-video', fake_video)
        page.click('#video-form button')
        page.wait_for_load_state('networkidle')
        check('media: invalid video rejected with validation error',
              'Please upload a valid video file.' in page.content() and
              page.locator('.video-model[data-name="e2e-fake-video"]').count() == 0)
        page.close()
    return manifest


def scenario_reupload_and_change(browser, manifest_v1):
    print('\n== collectstatic again, then modified CSS', flush=True)
    output = manage('collectstatic', '--noinput')
    check('collectstatic again uploads nothing', uploaded_count(output) == (0, FILES_COUNT), uploaded_count(output))

    write_theme(THEME_V2)
    output = manage('collectstatic', '--noinput')
    check('collectstatic after CSS change uploads only it', uploaded_count(output) == (1, FILES_COUNT - 1),
          uploaded_count(output))
    with open(os.path.join(E2E_DIR, 'manifest', 'staticfiles.json')) as f:
        manifest_v2 = json.load(f)['paths']
    check('manifest has new theme hash', manifest_v2['e2e/theme.css'] != manifest_v1['e2e/theme.css'],
          manifest_v2['e2e/theme.css'])

    with Server():
        page = browser.new_page()
        load(page, '/uploads/')
        check('uploads: modified theme CSS applied right away (blue h1)', css(page, 'h1', 'color') == BLUE)
        check('uploads: page uses new theme url', manifest_v2['e2e/theme.css'] in
              page.get_attribute('#extra-stylesheet', 'href'))
        page.close()

    print('\n== deleteredundantstatic', flush=True)
    old_theme = 'e2e-static/' + manifest_v1['e2e/theme.css']
    new_theme = 'e2e-static/' + manifest_v2['e2e/theme.css']
    output = manage('deleteredundantstatic', '--noinput')
    check('deleteredundantstatic deletes only old theme version',
          '1 files have been deleted successfully.' in output and old_theme in output, output.strip())
    check('old theme removed from Cloudinary', not resource_exists(old_theme, 'raw'))
    check('current theme kept in Cloudinary', resource_exists(new_theme, 'raw'))
    with Server():
        page = browser.new_page()
        failures = load(page, '/')
        check('index still works after cleanup', not failures and css(page, 'body', 'background-color') == GREEN,
              failures)
        page.close()


def scenario_unhashed_files():
    print('\n== UPLOAD_UNHASHED_STATIC_FILES', flush=True)
    output = manage('collectstatic', '--noinput', env={'E2E_UNHASHED': '1'})
    check('collectstatic with setting uploads unhashed files', uploaded_count(output) == (FILES_COUNT, FILES_COUNT),
          uploaded_count(output))
    url = 'https://res.cloudinary.com/{}/raw/upload/e2e-static/tests/css/style.css'.format(CLOUD)
    response = requests.get(url)
    check('unhashed file available under constant url', response.status_code == 200 and 'green' in response.text, url)
    output = manage('deleteredundantstatic', '--noinput', env={'E2E_UNHASHED': '1'})
    check('deleteredundantstatic keeps unhashed files with setting', 'There is no file to delete.' in output,
          output.strip())
    output = manage('deleteredundantstatic', '--noinput')
    check('deleteredundantstatic removes unhashed files without setting',
          '{} files have been deleted successfully.'.format(FILES_COUNT) in output, output.strip()[:200])


def scenario_debug(browser):
    print('\n== DEBUG=True serves local static files', flush=True)
    with Server(E2E_DEBUG='1'):
        page = browser.new_page()
        failures = load(page, '/')
        hrefs = static_hrefs(page)
        check('debug: no failed requests', not failures, failures)
        check('debug: static urls are local, unhashed',
              all(h.startswith(BASE + '/e2e-static/tests/') for h in hrefs if 'w_50' not in h), hrefs)
        check('debug: CSS applied', css(page, 'body', 'background-color') == GREEN)
        page.close()


def scenario_orphaned_media():
    print('\n== deleteorphanedmedia', flush=True)
    output = manage('shell', '-c', 'from tests.models import TestImageModel as M; m = M.objects.get(name="e2e-image"); '
                                   'print("NAMES", m.file.name, m.image.name); m.delete()')
    raw_name, image_name = re.search(r'NAMES (\S+) (\S+)', output).groups()
    output = manage('deleteorphanedmedia', '--noinput')
    check('deleteorphanedmedia deletes raw file and image of deleted model',
          '2 files have been deleted successfully.' in output and raw_name in output and image_name in output,
          output.strip())
    check('orphaned raw file removed from Cloudinary', not resource_exists(raw_name, 'raw'))
    check('orphaned image removed from Cloudinary', not resource_exists(image_name, 'image'))
    output = manage('deleteorphanedmedia', '--noinput')
    check('video still used by a model is kept', 'There is no file to delete.' in output, output.strip())


def cleanup():
    for tag in ('e2e-static', 'e2e-media'):
        for resource_type in ('raw', 'image', 'video'):
            cloudinary.api.delete_resources_by_tag(tag, resource_type=resource_type)
    shutil.rmtree(E2E_DIR, ignore_errors=True)


def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            manifest = scenario_hashed_static_and_media(browser)
            scenario_reupload_and_change(browser, manifest)
            scenario_unhashed_files()
            scenario_debug(browser)
            scenario_orphaned_media()
            browser.close()
    except Exception:
        traceback.print_exc()
        check('scenario finished without exception', False)
        server_log = os.path.join(E2E_DIR, 'server.log')
        if os.path.exists(server_log):
            print(open(server_log).read()[-3000:])
    finally:
        cleanup()
    failed = [r for r in results if not r[1]]
    print('\n{} checks, {} failed'.format(len(results), len(failed)))
    for name, _, detail in failed:
        print('  FAIL', name, detail)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
