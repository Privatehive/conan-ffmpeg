from conan import ConanFile, conan_version
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches, chdir, copy, export_conandata_patches, get, rename,
    replace_in_file, rm, rmdir, save, load
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import check_min_vs, is_msvc, unix_path
from conan.tools.scm import Git
import os
import glob
import shutil
import re
import json

required_conan_version = ">=2.0"


class FFMpegConan(ConanFile):
    jsonInfo = json.load(open("info.json", 'r'))
     # ---Package reference---
    name = jsonInfo["projectName"].lower()
    version = jsonInfo["version"]
    user = jsonInfo["domain"]
    channel = "stable"
    # ---Metadata---
    description = jsonInfo["projectDescription"]
    license = jsonInfo["license"]
    author = jsonInfo["vendor"]
    topics = jsonInfo["topics"]
    homepage = jsonInfo["homepage"]
    url = jsonInfo["repository"]
    # ---Sources---
    exports = ["info.json"]
    exports_sources = []
    # ---Requirements---
    tool_requires = ["ninja/[>=1.11.1]"]
    # ---Binary model---
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "avdevice": [True, False],
        "avcodec": [True, False],
        "avformat": [True, False],
        "swresample": [True, False],
        "swscale": [True, False],
        "postproc": [True, False],
        "avfilter": [True, False],
        "with_asm": [True, False],
        "with_zlib": [True, False],
        "with_openssl": [True, False],
        "disable_avdevice": [True, False],
        "disable_avcodec": [True, False],
        "disable_avformat": [True, False],
        "disable_swresample": [True, False],
        "disable_swscale": [True, False],
        "disable_postproc": [True, False],
        "disable_avfilter": [True, False],
        "enable_encoders": [None, "ANY"],
        "enable_decoders": [None, "ANY"],
        "enable_hardware_accelerators": [None, "ANY"],
        "enable_muxers": [None, "ANY"],
        "enable_demuxers": [None, "ANY"],
        "enable_parsers": [None, "ANY"],
        "enable_bitstream_filters": [None, "ANY"],
        "enable_protocols": [None, "ANY"],
        "enable_input_devices": [None, "ANY"],
        "enable_output_devices": [None, "ANY"],
        "enable_filters": [None, "ANY"],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "avdevice": False,
        "avcodec": False,
        "avformat": False,
        "swresample": False,
        "swscale": False,
        "postproc": False,
        "avfilter": False,
        "with_asm": True,
        "with_zlib": False,
        "with_openssl": False,
        "disable_avdevice": False,
        "disable_avcodec": False,
        "disable_avformat": False,
        "disable_swresample": False,
        "disable_swscale": False,
        "disable_postproc": False,
        "disable_avfilter": False,
        "enable_encoders": None,
        "enable_decoders": None,
        "enable_hardware_accelerators": None,
        "enable_muxers": None,
        "enable_demuxers": None,
        "enable_parsers": None,
        "enable_bitstream_filters": None,
        "enable_protocols": None,
        "enable_input_devices": None,
        "enable_output_devices": None,
        "enable_filters": None,
    }

    # ---Folders---
    no_copy_source = True

    @property
    def avbuild_arch(self):
        arch = {
            "x86": "x86",
            "x86_64": "x86_64" if self.settings.os == 'Android' else 'amd64',
            "armv8": "arm64" if self.settings.os == 'Macos' else 'armv8',
            "armv7": "armv7",
        }
        return arch.get(str(self.settings.arch))
    
    @property
    def avbuild_os(self):
        return str(self.settings.os).lower()
    
    @property
    def avbuild_compiler(self):
        compiler = {
            "gcc": "gcc",
            "clang": "clang",
            "apple-clang": "clang",
        }
        return compiler.get(str(self.settings.compiler))

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], destination="ffmpeg", strip_root=True)
    
    def build_requirements(self):
        if self.settings.os == 'Linux' or self.settings.os == 'Windows':
            if self.settings.arch == 'x86' or self.settings.arch == 'x86_64':
                self.tool_requires("nasm/2.16.01")
        if self._settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/cci.latest")

    def generate(self):
        ms = VirtualBuildEnv(self)
        ms.generate()

    def build(self):
        git = Git(self)
        git.clone(url="https://github.com/wang-bin/avbuild.git", args=["--recurse-submodules", "--shallow-submodules"], target="avbuild")
        git.folder = "avbuild"
        git.checkout("80373c7a7eecabfb479f6ff06fc4b3e0f22d6c79")

        f = open(os.path.join("avbuild", "config.sh"), "w")
        f.close()
        #shutil.copyfile(os.path.join("avbuild", "config-lite.sh"), os.path.join("avbuild", "config.sh"))

        env1 = Environment()
        env1.define("USE_TOOLCHAIN", self.avbuild_compiler)
        env1.define("FFSRC", self.source_folder + "/ffmpeg")

        options = ['--disable-autodetect', '--disable-programs', '--disable-doc', '--disable-libdrm', '--disable-everything']

        env1.define("USER_OPT", " ".join(options))

        #env1.define("DEC_OPT_MOBILE", "--enable-decoder=*sub*,movtext,*web*,aac*,ac3*,eac3*,alac*,ape,ass,av1*,ccaption,cfhd,cook,dca,dnxhd,exr,truehd,*yuv*,flv,flac,gif,h26[3-4]*,hevc*,hap,mp[1-3]*,prores,*[mj]peg*,mlp,mpl2,nellymoser,opus,pcm*,qtrle,*png*,tiff,rawvideo,rv*,sami,srt,ssa,v210*,vc1*,vorbis,vp[6-9]*,wm*,wrapped_avframe")

        with env1.vars(self).apply():
            self.run("%s %s %s" % (self.build_folder + "/avbuild/avbuild.sh", self.avbuild_os, self.avbuild_arch), cwd=os.path.join(self.build_folder, "avbuild"))

    def package(self):
        out_dir = "sdk-%s-%s-%s" % (self.avbuild_os, self.avbuild_arch, self.avbuild_compiler)
        print(out_dir)
        copy(self, "*", src=os.path.join(self.build_folder, "avbuild", out_dir), dst=self.package_folder)
