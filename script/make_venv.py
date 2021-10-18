from __future__ import annotations

import subprocess as sbp
import sys
import venv
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import SimpleNamespace

DEFAULT_PROMPT = "Cordy-Env"

class CordyEnvBuilder(venv.EnvBuilder):
    def __init__(self, system_site_packages: bool = False, clear: bool = False,
                 symlinks: bool = False, upgrade: bool = False,
                 prompt: str | None = DEFAULT_PROMPT, upgrade_deps: bool = False) -> None:

        if sys.version_info < (3, 9):
            raise Exception(
                "Cordy environments must use python 3.9 or above."
                "\nLatest cpython is available at https://www.python.org/downloads/"
            )

        super().__init__(
            system_site_packages=system_site_packages,
            clear=clear, symlinks=symlinks, upgrade=upgrade,
            with_pip=True, prompt=prompt,
            upgrade_deps=upgrade_deps
        )

    def setup_project_deps(self, context: SimpleNamespace) -> None:
        cmd = [context.env_exec_cmd, "-m"]

        sbp.run(cmd + "pip install poetry --upgrade".split(), stderr=sbp.STDOUT)
        sys.stdout.write("Installing Cordy dependecies ...\n")

        try:
            sbp.run(cmd + "poetry update".split(), capture_output=True, check=True)
        except sbp.CalledProcessError as err:
            sys.stdout.write(f"Poetry failed with error code {err.returncode}\n")

    def post_setup(self, context: SimpleNamespace) -> None:
        self.setup_project_deps(context)

def main(argv=None) -> int:
    import argparse
    import os

    parser = argparse.ArgumentParser(prog="Cordy-venv",
                                        description='Creates virtual Python '
                                                    'environments in one or '
                                                    'more target '
                                                    'directories.',
                                        epilog='Once an environment has been '
                                            'created, you may wish to '
                                            'activate it, e.g. by '
                                            'sourcing an activate script '
                                            'in its bin directory.')
    parser.add_argument('dirs', metavar='ENV_DIR', nargs='+',
                        help='A directory to create the environment in.')
    parser.add_argument('--system-site-packages', default=False,
                        action='store_true', dest='system_site',
                        help='Give the virtual environment access to the '
                                'system site-packages dir.')
    if os.name == 'nt':
        use_symlinks = False
    else:
        use_symlinks = True

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--symlinks', default=use_symlinks,
                        action='store_true', dest='symlinks',
                        help='Try to use symlinks rather than copies, '
                            'when symlinks are not the default for '
                            'the platform.')
    group.add_argument('--copies', default=not use_symlinks,
                        action='store_false', dest='symlinks',
                        help='Try to use copies rather than symlinks, '
                            'even when symlinks are the default for '
                            'the platform.')
    parser.add_argument('--clear', default=False, action='store_true',
                        dest='clear', help='Delete the contents of the '
                                            'environment directory if it '
                                            'already exists, before '
                                            'environment creation.')
    parser.add_argument('--upgrade', default=False, action='store_true',
                        dest='upgrade', help='Upgrade the environment '
                                            'directory to use this version '
                                            'of Python, assuming Python '
                                            'has been upgraded in-place.')
    parser.add_argument('--prompt',
                        help='Provides an alternative prompt prefix for '
                                'this environment.')
    parser.add_argument('--upgrade-deps', default=False, action='store_true',
                        dest='upgrade_deps')
    options = parser.parse_args(argv)

    if options.upgrade and options.clear:
        raise ValueError('you cannot supply --upgrade and --clear together.')

    builder = CordyEnvBuilder(
        system_site_packages=options.system_site,
        clear=options.clear,
        symlinks=options.symlinks,
        upgrade=options.upgrade,
        prompt=options.prompt,
        upgrade_deps=options.upgrade_deps
    )

    try:
        for d in options.dirs:
            builder.create(d)
    except Exception:
        return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())