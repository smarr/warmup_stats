#!/usr/bin/env python2.7
"""
usage: outlier_summaries.py [-h] [--latexfile LATEX_FILE] json_files

Summarise outlier information stored within a Krun results file.

Example usage:

    $ python outlier_summaries.py bencher_results.json.bz2
    $ python outlier_summaries.py results.json.bz2 -l summary.tex

positional arguments:
  json_files            One or more Krun result files.

optional arguments:
  -h, --help            show this help message and exit
  --latexfile LATEX_FILE, -l LATEX_FILE
                        Name of the LaTeX file to write to.
"""

import argparse
import bz2
import json
import os
import os.path


LATEX_FILENAME = 'outlier_summary_tables.tex'

__LATEX_HEADER = lambda window_size: """
\documentclass[12pt]{article}
\usepackage{longtable}
\usepackage{booktabs}
\\title{Summaries of outlier counts. Window size: %s}
\\begin{document}
\maketitle
""" % window_size

__LATEX_SECTION = lambda section: """
\\section*{%s}
""" % section

__LATEX_START_TABLE = lambda col_title: """
\\begin{center}
\\begin{longtable}{l|r}
\\toprule
%s & Number of outliers \\\\
\midrule
\endfirsthead
\\toprule
%s & Number of outliers \\\\
\midrule
\endhead
\midrule
\endfoot
\\bottomrule
\endlastfoot
""" % (col_title, col_title)

__LATEX_END_TABLE = """
\end{longtable}
\end{center}
"""

__LATEX_FOOTER = """
\end{document}
"""


def main(data_dcts, window_size, latex_file):
    """Count outliers for all window size / percentile configurations.
    Save results in a JSON file.
    """
    outlier_summary = {'benchmarks':dict(), 'vms':dict(), 'variants':dict()}
    common_summary = {'benchmarks':dict(), 'vms':dict(), 'variants':dict()}
    unique_summary = {'benchmarks':dict(), 'vms':dict(), 'variants':dict()}
    for machine in data_dcts:
        keys = sorted(data_dcts[machine]['all_outliers'].keys())
        for key in keys:
            bench, vm, variant = key.split(':')
            if bench not in outlier_summary['benchmarks']:
                outlier_summary['benchmarks'][bench] = 0
                common_summary['benchmarks'][bench] = 0
                unique_summary['benchmarks'][bench] = 0
            if vm not in outlier_summary['vms']:
                outlier_summary['vms'][vm] = 0
                common_summary['vms'][vm] = 0
                unique_summary['vms'][vm] = 0
            if variant not in outlier_summary['variants']:
                outlier_summary['variants'][variant] = 0
                common_summary['variants'][variant] = 0
                unique_summary['variants'][variant] = 0
            all_executions = data_dcts[machine]['all_outliers'][key]
            common_executions = data_dcts[machine]['common_outliers'][key]
            unique_executions = data_dcts[machine]['unique_outliers'][key]
            if len(all_executions) == 0:
                continue  # Benchmark skipped
            elif len(all_executions[0]) == 0:
                continue  # Benchmark crashed.
            else:
                for outlier_list in all_executions:
                    outlier_summary['benchmarks'][bench] += len(outlier_list)
                    outlier_summary['vms'][vm] += len(outlier_list)
                    outlier_summary['variants'][variant] += len(outlier_list)
                for outlier_list in common_executions:
                    common_summary['benchmarks'][bench] += len(outlier_list)
                    common_summary['vms'][vm] += len(outlier_list)
                    common_summary['variants'][variant] += len(outlier_list)
                for outlier_list in unique_executions:
                    unique_summary['benchmarks'][bench] += len(outlier_list)
                    unique_summary['vms'][vm] += len(outlier_list)
                    unique_summary['variants'][variant] += len(outlier_list)
    # Write out results.
    write_results_as_latex(outlier_summary, common_summary, unique_summary,
                           window_size, latex_file)
    return


def _tex_escape(word):
    return word.replace('_', '\\_')


def write_results_as_latex(outlier_summary, common_summary, unique_summary,
                           window_size, tex_file):
    """Write a results file.
    """
    print('Writing data to %s.' % tex_file)
    with open(tex_file, 'w') as fp:
        sections = (('All outliers', outlier_summary),
                    ('Common outliers', common_summary),
                    ('Unique outliers (only appear in one process execution)',
                     unique_summary))
        # Preamble.
        fp.write(__LATEX_HEADER(str(window_size)))
        # Write out all sections.
        for section_heading, summary in sections:
            # Section heading.
            fp.write(__LATEX_SECTION(section_heading))
            # Outliers per benchmark.
            fp.write(__LATEX_START_TABLE('Benchmark'))
            for bench in summary['benchmarks']:
                fp.write('%s & %d \\\\ \n' %
                         (_tex_escape(bench), summary['benchmarks'][bench]))
            fp.write(__LATEX_END_TABLE)
            # Outliers per VM.
            fp.write(__LATEX_START_TABLE('Virtual machine'))
            for vm in summary['vms']:
                fp.write('%s & %d \\\\ \n' %
                         (_tex_escape(vm), summary['vms'][vm]))
            fp.write(__LATEX_END_TABLE)
            # Outliers per language variant.
            fp.write(__LATEX_START_TABLE('Language variant'))
            for variant in summary['variants']:
                fp.write('%s & %d \\\\ \n' %
                         (_tex_escape(variant), summary['variants'][variant]))
            fp.write(__LATEX_END_TABLE)
        # End document.
        fp.write(__LATEX_FOOTER)
    return


def read_krun_results_file(results_file):
    """Return the JSON data stored in a Krun results file.
    """
    results = None
    with bz2.BZ2File(results_file, 'rb') as file_:
        results = json.loads(file_.read())
        return results
    return None


def get_data_dictionaries(json_files):
    """Read a list of BZipped JSON files and return their contents as a
    dictionaries of machine name -> JSON values.
    """
    data_dictionary = dict()
    window_size = None
    for filename in json_files:
        assert os.path.exists(filename), 'File %s does not exist.' % filename
        print('Loading: %s' % filename)
        data = read_krun_results_file(filename)
        machine_name = data['audit']['uname'].split(' ')[1]
        if '.' in machine_name:  # Remove domain, if there is one.
            machine_name = machine_name.split('.')[0]
        data_dictionary[machine_name] = data
        if window_size is None:
            window_size = data['window_size']
        else:
            assert window_size == data['window_size'], \
                   ('Cannot summarise outliers generated with different' +
                    ' window sizes.')
    return window_size, data_dictionary


def create_cli_parser():
    """Create a parser to deal with command line switches.
    """
    script = os.path.basename(__file__)
    description = (('Summarise outlier information stored within a Krun ' +
                    'results file.' +
                    '\n\nExample usage:\n\n' +
                    '\t$ python %s results.json.bz2\n' +
                    '\t$ python %s -l summary.tex results.json.bz2')
                   % (script, script))
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('json_files',
                        action='append',
                        nargs='+',
                        default=[],
                        type=str,
                        help='One or more Krun result files.')
    parser.add_argument('--latexfile', '-l',
                        action='store',
                        dest='latex_file',
                        default=LATEX_FILENAME,
                        type=str,
                        help=('Name of the LaTeX file to write to.'))
    return parser


if __name__ == '__main__':
    parser = create_cli_parser()
    options = parser.parse_args()
    window_size, data_dcts = get_data_dictionaries(options.json_files[0])
    main(data_dcts, window_size, options.latex_file)