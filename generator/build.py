"""Regenere toute la banniere en une commande.

    python generator/build.py

Enchaine les trois etapes et reaffiche les metriques de verification. Le
script et les .npy sont la source de verite : ne jamais editer les SVG a la
main, ils sont ecrases a chaque execution.
"""
import runpy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

for step in ('prepare', 'morph', 'build_banner'):
    print('=' * 62)
    print('  %s' % step)
    print('=' * 62)
    runpy.run_module(step, run_name='__main__')
    print()
