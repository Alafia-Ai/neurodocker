"""Class to add Miniconda and create Conda environment."""
# Author: Jakub Kaczmarzyk <jakubk@mit.edu>

# Refer to the jupyter base-notebook Dockerfile for good practices:
# https://github.com/jupyter/docker-stacks/blob/master/base-notebook/Dockerfile

from __future__ import absolute_import, division, print_function
import logging
import posixpath

from neurodocker.utils import check_url, indent

logger = logging.getLogger(__name__)


class Miniconda(object):
    """Add Dockerfile instructions to install Miniconda and create a new
    environment with packages installed with conda and pip.

    Parameters
    ----------
    env_name : str
        Name to give this environment.
    python_version : str
        Version of Python to install. For example, '3.6.1'.
    pkg_manager : {'apt', 'yum'}
        Linux package manager.
    conda_install : str or list or tuple
        Packages to install using `conda`. Follow the syntax for
        `conda install`. For example, the input ['numpy=1.12', 'scipy'] is
        interpreted as `conda install numpy=1.12 scipy`. The conda-forge
        channel is added by default.
    pip_install : str or list or tuple
        Packages to install using `pip`. Follow the syntax for `pip install`.
        For example, the input "https://github.com/nipy/nipype/" is interpreted
        as `pip install https://github.com/nipy/nipype/`.
    add_to_path : bool
        If true, prepend the new environment to $PATH.
    miniconda_verion : str
        Version of Miniconda to install. Defaults to 'latest'. This does not
        correspond to Python version.
    check_urls : bool
        If true, raise error if a URL used by this class responds with an error
        code.

    Notes
    -----
    Miniconda is installed once by the root user in /opt/conda. Separate conda
    environments can be created by non-root users.
    """

    installed = False
    INSTALL_PATH = "/opt/conda"

    def __init__(self, env_name, python_version, pkg_manager,
                 conda_install=None, pip_install=None, add_to_path=True,
                 miniconda_verion='latest', check_urls=True):
        self.env_name = env_name
        self.python_version = python_version
        self.pkg_manager = pkg_manager
        self.conda_install = conda_install
        self.pip_install = pip_install
        self.add_to_path = add_to_path
        self.miniconda_verion = miniconda_verion
        self.check_urls = check_urls

        # ENV instruction does not expand $HOME.
        # https://github.com/moby/moby/issues/28971

        # self._env_name = "default"
        # self._env_path = posixpath.join(self._install_path, "envs",
        #                                 self._env_name)
        self.cmd = self._create_cmd()

    def _create_cmd(self):
        cmds = []
        comment = ("#------------------"
                   "\n# Install Miniconda"
                   "\n#------------------")
        if not Miniconda.installed:
            cmds.append(comment)
            cmds.append(self.install_miniconda())
            cmds.append('')

        comment = ("#-------------------------"
                   "\n# Create conda environment"
                   "\n#-------------------------")
        cmds.append(comment)
        cmds.append(self.create_conda_env())

        return "\n".join(cmds)

    def install_miniconda(self):
        """Return Dockerfile instructions to install Miniconda."""

        install_url = ("https://repo.continuum.io/miniconda/"
                       "Miniconda3-{}-Linux-x86_64.sh"
                       "".format(self.miniconda_verion))
        if self.check_urls:
            check_url(install_url)

        env_cmd = ("CONDA_DIR={0}"
                   "\nPATH={0}/bin:$PATH".format(Miniconda.INSTALL_PATH))
        env_cmd = indent("ENV", env_cmd)

        cmd = ('echo "Downloading Miniconda installer ..."'
               "\n&& miniconda_installer=/tmp/miniconda.sh"
               "\n&& curl -sSL -o $miniconda_installer {url}"
               "\n&& /bin/bash $miniconda_installer -f -b -p $CONDA_DIR"
               "\n&& rm -f $miniconda_installer"
               "\n&& conda config --system --prepend channels conda-forge"
               "\n&& conda config --system --set auto_update_conda false"
               "\n&& conda config --system --set show_channel_urls true"
               "\n&& conda update -y --all"
               "\n&& conda clean -tipsy"
               "".format(url=install_url))
        cmd = indent("RUN", cmd)

        Miniconda.installed = True

        return "\n".join((env_cmd, cmd))

    def create_conda_env(self):
        """Return Dockerfile instructions to create conda environment with
        desired version of Python and desired conda and pip packages.
        """
        cmd = ("conda create -y -q --name {} python={}"
               "".format(self.env_name, self.python_version))
        if self.conda_install:
            if isinstance(self.conda_install, (list, tuple)):
                self.conda_install = " ".join(self.conda_install)
            cmd += "\n\t{}".format(self.conda_install)

        cmd += "\n&& conda clean -tipsy"

        if self.pip_install:
            cmd += self._install_pip_pkgs()

        cmd = indent("RUN", cmd)

        if self.add_to_path:
            bin_path = posixpath.join(Miniconda.INSTALL_PATH, 'envs',
                                      self.env_name, 'bin')
            env_cmd = "ENV PATH={}:$PATH".format(bin_path)
            return "\n".join((cmd, env_cmd))
        return cmd

    def _install_pip_pkgs(self):
        """Return Dockerfile instruction to install desired pip packages."""
        if isinstance(self.pip_install, (list, tuple)):
            self.pip_install = " ".join(self.pip_install)
        cmd = ('\n&& /bin/bash -c "source activate {}'
               '\n\t&& pip install -q --no-cache-dir\n\t{}"'
               "".format(self.env_name, self.pip_install))
        return cmd

    @classmethod
    def clear_memory(cls):
        cls.installed = False