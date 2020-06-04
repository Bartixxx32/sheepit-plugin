# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import sys
import os
import requests.sessions
import requests.cookies
import html.parser


class NetworkException(Exception):
    pass


class LoginException(Exception):
    pass


class UploadException(Exception):
    pass


class Sheepit():
    """ Api for Managing your SheepIt Account
        and uploading Project """

    def __init__(self):
        self.domain = "www.sheepit-renderfarm.com"
        self.session = requests.session()

    def __del__(self):
        self.session.close()
        del self.session

    def login(self, username, password):
        """ This method try's logging in with the provided
            username and password

            For continuing a connection, please use import_session()
            Use logout() to logout

            Raises:
            NetworkError on a failed connection
            LoginError on a Wrong username and/or password """
        try:
            r = self.session.post(f"https://{self.domain}/ajax.php",
                                  data={"login": username,
                                        "password": password,
                                        "do_login": "do_login",
                                        "timezone": "Europe/Berlin",
                                        "account_login": "account_login"},
                                  timeout=5)
        except requests.exceptions.Timeout:
            raise NetworkException("Timed out")
        except requests.exceptions.RequestException:
            raise NetworkException("Failed connecting to the sheepit server")
        if r.text != "OK":
            raise LoginException("Wrong Username and/or Password")
        return

    def logout(self):
        """ When run, this method will send a logout request to the Server
            Additionally all Cookies will be cleared

            Use login() to login

            Raises:
            NetworkError on a failed connection,
                cookies will still be cleared """
        try:
            self.session.get(
                f"https://{self.domain}/account.php?mode=logout", timeout=5)
        except requests.exceptions.Timeout:
            raise NetworkException("Timed out")
        except requests.exceptions.RequestException:
            raise NetworkException("Failed connecting to the sheepit server")
        finally:
            try:
                self.session.cookies.clear(domain=self.domain)
            except KeyError:
                pass

    def request_upload_token(self):
        """ Requests a upload token from the Server
            This token should be used with:

            upload_file() and
            add_job()

            Raises:
            NetworkError on a failed connection
            UploadException if the maximum number of simultaneous
                projects had been reached """
        try:
            r = self.session.get(f"https://{self.domain}/getstarted.php",
                                 timeout=5)
        except requests.exceptions.Timeout:
            raise NetworkException("Timed out")
        except requests.exceptions.RequestException:
            raise NetworkException("Failed connecting to the sheepit server")

        p = TokenParser()
        p.feed(str(r.text))
        p.close()
        if p.token == "":
            raise UploadException("Error getting Upload Token")
        return p.token

    def upload_file(self, token, path_to_file):
        """ Uploads the selected file to the Server

            Use request_upload_token() to get a token
            and add_job() to add the uploaded project

            Raises:
            NetworkError on a failed connection """
        try:
            r = self.session.post(
                f"https://{self.domain}/jobs.php", data={
                    "step": "1",
                    "transfertmethod": "File",
                    "token": token,
                    "PHP_SESSION_UPLOAD_PROGRESS": token,
                    "mode": "add",
                },
                files={"addjob_archive": (os.path.split(path_to_file)[1], open(
                    path_to_file, "rb"))}
            )
        except requests.exceptions.RequestException:
            raise NetworkException("Failed connecting to the sheepit server")

    def add_job(self, token, animation=True, cpu=True, cuda=False,
                opencl=False, public=True, mp4=False,
                anim_start_frame=None, anim_end_frame=None,
                anim_step_frame=None, still_frame=None, max_ram=None,
                split=None):
        """ Uploads the selected file to the Server

            Use request_upload_token() to get a token
            and upload_file() to upload the file

            Raises:
            NetworkError on a failed connection """
        param_start_frame = 0
        param_end_frame = 0
        param_step_frame = 1

        if animation:
            param_start_frame = anim_start_frame
            param_end_frame = anim_end_frame
            param_step_frame = anim_step_frame
        else:
            param_start_frame = still_frame

        try:
            r = self.session.get(
                f"https://{self.domain}/jobs.php?mode=add&step=2&token={token}")
        except requests.exceptions.RequestException:
            raise NetworkException("Failed connecting to the sheepit server")
        parser = AddJobParser()
        parser.feed(str(r.text))
        parser.close()

        compute_method = 0
        if parser.data['addjob_engine_0'] == "BLENDER_EEVEE":
            cpu = False
        if cpu:
            compute_method += 1
        if cuda:
            compute_method += 2
        if opencl:
            compute_method += 4

        settings = {
            "addjob": "addjob",
            "do_addjob": "do_addjob",
            "token": token,
            "type": "animation" if animation else "singleframe",
            "compute_method": compute_method,
            "executable": "blender283",
            "engine": parser.data['addjob_engine_0'],
            "public_render": "1" if public else "0",
            "public_thumbnail": "0",
            "generate_mp4": "1" if mp4 else "0",
            "start_frame": param_start_frame,
            "end_frame": param_end_frame,
            "step_frame": param_step_frame,
            "archive": parser.data['addjob_archive_0'],
            "max_ram_optional": "",
            "path": parser.data['addjob_path_0'],
            "framerate": parser.data['addjob_framerate_0'],
            "split_tiles": split,
            "exr": "0",
            "cycles_samples": parser.data['addjob_cycles_samples_0'],
            "samples_pixel": parser.data['addjob_samples_pixel_0'],
            "image_extension": parser.data['addjob_image_extension_0'],
        }
        try:
            r = self.session.post(
                f"https://{self.domain}/ajax.php", data=settings)
        except requests.exceptions.RequestException:
            raise NetworkException("Failed connecting to the sheepit server")

    def import_session(self, dict):
        """ Imports all cookies from a dictionary

        Use export_session() to export """
        for name, value in dict.items():
            self.session.cookies.set_cookie(requests.cookies.create_cookie(
                domain=self.domain,
                name=name,
                value=value
            ))

    def export_session(self):
        """ Exports all cookies as a dictionary

        Use import_session() to import """
        cookies = dict()
        for cookie in self.session.cookies:
            if cookie.domain == self.domain:
                cookies[cookie.name] = cookie.value
        return cookies


class TokenParser(html.parser.HTMLParser):
    """ Parses the get started page to return a upload token """

    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.token = ""

    def handle_starttag(self, tag, attributes):
        if tag == 'input':
            isToken = False
            for name, value in attributes:
                if(name == "name" and value == "token"):
                    isToken = True
            if isToken:
                for name, value in attributes:
                    if(name == "value"):
                        self.token = value


class AddJobParser(html.parser.HTMLParser):
    """ Parses the step 2 Page in the upload process """

    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.data = {
            "addjob_engine_0": "",
            "addjob_archive_0": "",
            "addjob_path_0": "",
            "addjob_framerate_0": "",
            "addjob_cycles_samples_0": "",
            "addjob_samples_pixel_0": "",
            "addjob_image_extension_0": "",
        }

    def handle_starttag(self, tag, attributes):
        if tag == 'input':
            is_valid = False
            id = ""
            for name, value in attributes:
                if(name == "id" and (value in self.data)):
                    is_valid = True
                    id = value
            if is_valid:
                for name, value in attributes:
                    if(name == "value"):
                        self.data[id] = value