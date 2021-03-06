import unittest
from unittest.mock import MagicMock, patch

import subprocess

from pushapkscript import jarsigner
from pushapkscript.exceptions import SignatureError


class JarSignerTest(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.context.config = {
            'jarsigner_binary': '/path/to/jarsigner',
            'jarsigner_key_store': '/path/to/keystore',
            'jarsigner_certificate_aliases': {
                'aurora': 'aurora_alias',
                'beta': 'beta_alias',
                'release': 'release_alias',
                'dep': 'dep_alias',
            },
            'taskcluster_scope_prefix': 'project:releng:googleplay:',
        }
        self.context.task = {
            'scopes': ['project:releng:googleplay:aurora'],
        }

        self.minimal_context = MagicMock()
        self.minimal_context.config = {
            'jarsigner_key_store': '/path/to/keystore',
            'taskcluster_scope_prefix': 'project:releng:googleplay:',
        }
        self.minimal_context.task = {
            'scopes': ['project:releng:googleplay:aurora'],
        }

    def test_verify_should_call_executable_with_right_arguments(self):
        for android_product, alias in self.context.config['jarsigner_certificate_aliases'].items():
            self.context.task['scopes'] = ['project:releng:googleplay:{}'.format(android_product)]
            with patch('subprocess.run') as run:
                run.return_value = MagicMock()
                run.return_value.returncode = 0
                run.return_value.stdout = '''
                    smk      632 Mon Feb 01 12:54:21 CET 2016 application.ini
                        Digest algorithm: SHA1
                '''
                jarsigner.verify(self.context, '/path/to/apk')

                run.assert_called_with([
                    '/path/to/jarsigner', '-verify', '-strict', '-verbose', '-keystore', '/path/to/keystore', '/path/to/apk', alias
                ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def test_verify_should_call_executable_with_defaults_arguments(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 0
            run.return_value.stdout = 'Digest algorithm: SHA1'
            jarsigner.verify(self.minimal_context, '/path/to/apk')

            run.assert_called_with([
                'jarsigner', '-verify', '-strict', '-verbose', '-keystore', '/path/to/keystore', '/path/to/apk', 'nightly'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def test_raises_error_when_return_code_is_not_0(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 1

            with self.assertRaises(SignatureError):
                jarsigner.verify(self.context, '/path/to/apk')

    def test_raises_error_when_digest_is_not_sha1_for_fennec(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 0
            run.return_value.stdout = 'Digest algorithm: SHA-256'

            with self.assertRaises(SignatureError):
                jarsigner.verify(self.context, '/path/to/apk')

    def test_expects_sha256_for_focus_or_klar(self):
        self.context.task['scopes'] = ['project:mobile:focus:releng:product:focus']
        self.context.config['taskcluster_scope_prefix'] = 'project:mobile:focus:releng:product:'
        self.context.config['jarsigner_certificate_aliases']['focus'] = 'focus'
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 0
            run.return_value.stdout = 'Digest algorithm: SHA-256'

            jarsigner.verify(self.context, '/path/to/apk')

    def test_raises_error_when_no_digest_algo_is_returned_by_jarsigner(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 0
            run.return_value.stdout = 'Some random output'

            with self.assertRaises(SignatureError):
                jarsigner.verify(self.context, '/path/to/apk')

    def test_pluck_configuration_sets_every_argument(self):
        self.assertEqual(
            jarsigner._pluck_configuration(self.context),
            (
                '/path/to/jarsigner',
                '/path/to/keystore',
                {
                    'aurora': 'aurora_alias',
                    'beta': 'beta_alias',
                    'release': 'release_alias',
                    'dep': 'dep_alias',
                },
                'aurora'
            )
        )

    def test_pluck_configuration_uses_defaults(self):
        self.assertEqual(
            jarsigner._pluck_configuration(self.minimal_context),
            (
                'jarsigner',
                '/path/to/keystore',
                {
                    'aurora': 'nightly',
                    'beta': 'nightly',
                    'release': 'release',
                    'dep': 'dep',
                },
                'aurora'
            )
        )
