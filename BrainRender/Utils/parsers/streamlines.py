import sys
sys.path.append('./')

import os
import json
from vtkplotter import *
import gzip

import pandas as pd
from tqdm import tqdm
import numpy as np

from BrainRender.Utils.data_io import load_json
from BrainRender.Utils.data_manipulation import get_coords
from BrainRender.colors import *
from BrainRender.variables import *
from BrainRender.Utils.webqueries import request
from BrainRender.Utils.ABA.connectome import ABA


class StreamlinesAPI(ABA):
    """
        [Takes care of downloading streamliens data and other useful stuff]
    """
    base_url = "https://neuroinformatics.nl/HBP/allen-connectivity-viewer/json/streamlines_NNN.json.gz"

    def __init__(self):
        ABA.__init__(self)

    def download_streamlines_for_region(self, region, *args, **kwargs):
        """
            [ Given the acronym for a region, it downloads the relevant streamlines data]
        """
        region_experiments = self.experiments_source_search(region, *args, **kwargs)
        return self.download_streamlines(region_experiments.id.values)


    @staticmethod
    def make_url_given_id(expid):
        return "https://neuroinformatics.nl/HBP/allen-connectivity-viewer/json/streamlines_{}.json.gz".format(expid)

    def extract_ids_from_csv(self, csv_file, download=False, **kwargs):
        """
            [Parse CSV file to extract experiments IDs and link to downloadable streamline data

            Given a CSV file with info about experiments downloaded from: http://connectivity.brain-map.org
            extract experiments ID and get links to download (compressed) streamline data from https://neuroinformatics.nl. 
            Also return the experiments IDs to download data from: https://neuroinformatics.nl/HBP/allen-connectivity-viewer/streamline-downloader.html
            ]

            Arguments:
                csv_file {[str]} --  [Path to a csv file.]
        """

        try:
            data = pd.read_csv(csv_file)
        except:
            raise FileNotFoundError("Could not load: {}".format(csv_file))
        else:
            if not download:
                print("Found {} experiments.\n".format(len(data.id.values)))

        if not download: 
            print("To download compressed data, click on the following URLs:")
            for eid in data.id.values:
                url = self.make_url_given_id(eid)
                print(url)

            print("\n")
            string = ""
            for x in data.id.values:
                string += "{},".format(x)

            print("To download JSON directly, go to: https://neuroinformatics.nl/HBP/allen-connectivity-viewer/streamline-downloader.html")
            print("and  copy and paste the following experiments ID in the 'Enter the Allen Connectivity Experiment number:' field.")
            print("You can copy and paste each individually or a list of IDs separated by a comma")
            print("IDs: {}".format(string[:-1]))
            print("\n")

            return data.id.values
        else:
            return self.download_streamlines(data.id.values, **kwargs)

    def download_streamlines(self, eids, streamlines_folder=None):
        if streamlines_folder is None:
            streamlines_folder = self.streamlines_cache

        if not isinstance(eids, (list, np.ndarray, tuple)): eids = [eids]

        filepaths, data = [], []
        for eid in eids:
            url = self.make_url_given_id(eid)
            jsonpath = os.path.join(streamlines_folder, str(eid)+".json")
            filepaths.append(jsonpath)
            if not os.path.isfile(jsonpath):
                response = request(url)

                # Write the response content as a temporary compressed file
                temp_path = os.path.join(streamlines_folder, "temp.gz")
                with open(temp_path, "wb") as temp:
                    temp.write(response.content)

                # Open in pandas and delete temp
                url_data = pd.read_json(temp_path, lines=True, compression='gzip')
                os.remove(temp_path)

                # save json
                url_data.to_json(jsonpath)

                # append to lists and return
                data.append(url_data)
            else:
                data.append(pd.read_json(jsonpath))
        return filepaths, data



def parse_streamline(*args, filepath=None, data=None, show_injection_site=True, color='ivory', alpha=.8, radius=10, **kwargs):
    """
        [Given a path to a .json file with streamline data, render the streamline as tubes actors.]

        Arguments:
            filepath {[str, list]} -- [Either a path to a .json file or a list of file paths]
            data {[pd.DataFrame, list]} -- [Either a dataframe or a list of dataframes with streamlines data]

        Keyword arguments:
            color {[str, color]} -- [Color of the streamlines actors]
            alpha {[float]} -- [range 0,1  transparency of the streamlines]
            radius {[int]} -- [radius of the tubes used to render the streamlines]
            show_injection_site {[bool]} -- [If true a sphere is rendered at the coordinates for the injection site]
    """
    if filepath is not None and data is None:
        data = load_json(filepath)
    elif filepath is None and data is not None:
        pass
    else:
        raise ValueError("Need to pass eiteher a filepath or data argument to parse_streamline")

    # create actors for streamlines
    lines = []
    if len(data['lines']) == 1:
        lines_data = data['lines'][0]
    else:
        lines_data = data['lines']
    for line in lines_data:
        points = [[l['x'], l['y'], l['z']] for l in line]
        lines.append(shapes.Tube(points,  r=radius, c=color, alpha=alpha, res=NEURON_RESOLUTION))

    # TODO add injections rendering

    merged = merge(*lines)
    merged.color(color)
    return [merged]










