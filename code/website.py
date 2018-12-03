"""
Simple website form for using BPTool online. Can be hosted
by running "python website.py"
"""
import csv
import cherrypy
import numpy as np
import os
import shutil
import pandas as pd

import bctool

CODE_DIR = os.path.dirname(os.path.realpath(__file__))

# Serving static files with CherryPy is a bit kludgy no matter how you do it,
#   so let's just do it directly:
with open(os.path.join(CODE_DIR, 'index.html'), 'r') as content_file:
    index_string = content_file.read()

class BCToolPage:
    @cherrypy.expose
    def index(self):
        # Ask for the parameters required for the Bayesian Audit.
        # Style parameters from 
        # https://www.w3schools.com/css/tryit.asp?filename=trycss_forms
        return index_string

    @cherrypy.expose
    def ComparisonAudit(
        self, collections, reported_votes, sample, seed, num_trials):

        if seed == '':
            seed = 1
        seed = int(seed)

        if num_trials == '':
            num_trials = 25000
        num_trials = int(num_trials)

        if not os.path.exists("tmp_files"):
            os.mkdir("tmp_files")

        collections_filename = 'tmp_files/' + collections.filename
        reported_votes_filename = 'tmp_files/' + reported_votes.filename
        sample_filename = 'tmp_files/' + sample.filename
   
        collections_data = collections.file.read()
        collections_file = open(
            collections_filename, 'wb')
        collections_file.write(collections_data)
        collections_file.close()

        reported_data = reported_votes.file.read()
        reported_data_file = open(
            reported_votes_filename, 'wb')
        reported_data_file.write(reported_data)
        reported_data_file.close()

        sample_data = sample.file.read()
        sample_data_file = open(
            sample_filename, 'wb')
        sample_data_file.write(sample_data)
        sample_data_file.close()

        collection_names, collection_size, collections_rows = \
            bctool.read_and_process_collections(collections_filename)

        reported_choices, reported_size, reported_rows = \
            bctool.read_and_process_reported(reported_votes_filename,
                                             collection_names,
                                             collection_size,
                                             collections_filename)
        actual_choices, sample_dict, sample_rows = \
            bctool.read_and_process_sample(sample_filename,
                                           collection_names,
                                           reported_choices)

        shutil.rmtree("tmp_files")

        # Stratify by (collection, choice) pairs
        strata = []                 # list of (collection, reported_choice) pairs
        strata_size = []            # corresponding list of # reported votes
        for collection in collection_names:
            for reported_choice in reported_choices:
                stratum = (collection, reported_choice)
                strata.append(stratum)
                # Record stratum size (number of votes reported cast)
                strata_size.append(reported_size[collection][reported_choice])

        # create sample tallies for each strata
        strata_sample_tallies = []
        strata_pseudocounts = []
        for (collection, reported_choice) in strata:
            stratum_sample_tally = []
            stratum_pseudocounts = []
            for actual_choice in actual_choices:
                count = sample_dict[collection][reported_choice][actual_choice]
                stratum_sample_tally.append(count)
                if reported_choice == actual_choice:
                    # Default pseudocount_match = 50
                    stratum_pseudocounts.append(50)
                else:
                    # Default pseudocount base = 1
                    stratum_pseudocounts.append(1)
            strata_sample_tallies.append(np.array(stratum_sample_tally))
            strata_pseudocounts.append(np.array(stratum_pseudocounts))

        # Default value for n winners
        n_winners = 1

        win_probs = bctool.compute_win_probs(
                        strata_sample_tallies,
                        strata_pseudocounts,
                        strata_size,
                        seed,
                        num_trials,
                        actual_choices,
                        n_winners)
        return self.get_html_results(actual_choices, win_probs, n_winners)

    def get_html_results(self, actual_choices, win_probs, n_winners):
        """
        Given list of candidate_names and win_probs pairs, print summary
        of the Bayesian audit simulations.

        Input Parameters:

        -candidate_names is an ordered list of strings, containing the name of
        every candidate in the contest we are auditing.

        -win_probs is a list of pairs (i, p) where p is the fractional
        representation of the number of trials that candidate i has won
        out of the num_trials simulations.

        Returns:

        -String of HTML formatted results, which make a table on the online
        BPTool.
        """

        results_str = (
            '<style> \
            table, th, td { \
                     border: 1px solid black; \
            }\
            </style>\
            <h1> BCTOOL (Bayesian ballot-comparison tool version 0.8) </h1>')

        want_sorted_results = True
        if want_sorted_results:
            sorted_win_probs = sorted(
                win_probs, key=lambda tup: tup[1], reverse=True)
        else:
            sorted_win_probs = win_probs

        results_str += '<table style="width:100%">'
        results_str += '<tr>'
        results_str += ("<th>{:<24s}</th> <th>{:<s}</th>"
              .format("Choice",
                      "Estimated probability of winning a full manual recount"))
        results_str += '</tr>'

        for choice_index, prob in sorted_win_probs:
            choice = str(actual_choices[choice_index - 1])
            results_str += '<tr>'
            results_str += ('<td style="text-align:center">{:<24s}</td>').format(choice)
            results_str += ('<td style="text-align:center">{:6.2f} %</td>').format(100*prob)
            results_str += '</tr>'
        results_str += '</table>'
        results_str += '<p> Click <a href="./">here</a> to go back to the main page.</p>'
        return results_str



server_conf = os.path.join(CODE_DIR, 'server_conf.conf')

if __name__ == '__main__':
    # cherrypy.tree.mount(BCToolPage(),  config=server_conf)
    # cherrypy.engine.start()
    # cherrypy.engine.block()

    # cherrypy.config.update({'tools.sessions.on': True,
    #                     'tools.sessions.storage_type': "File",
    #                     'tools.sessions.storage_path': 'sessions',
    #                     'tools.sessions.timeout': 10
    #            })
    cherrypy.quickstart(BCToolPage(), config=server_conf)
