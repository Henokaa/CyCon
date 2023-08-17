import os
import sys
import csv
from pathlib import Path
import json
from flask import Blueprint
from flask import Flask, request, render_template, g, redirect, url_for, flash
from flask import session
from mysql.connector import Error
from flask import current_app
from flask import jsonify
import logging
from pathlib import Path

from sympy.printing.latex import latex
import sympy

import pandas as pd
import numpy as np
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

from sklearn.metrics import accuracy_score, f1_score, precision_score

from sklearn.metrics import ConfusionMatrixDisplay
from sklearn.metrics import confusion_matrix

# Models
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from werkzeug.utils import secure_filename

from backend.calculator import Calculator, read_data

from backend.db import DBManager

# sys.path.append("backend")
# sys.path.append("Classes")
# sys.path.insert(1, '/Classes/')
from backend import MLA
from backend import Validation
from backend.Classes.PreoptimizationFiles import Preoptimization
from backend.Classes.PreoptimizationFiles import Standardization
from backend.Classes.NeuralNetworkFiles import NeuralNetwork
from backend.Classes.NeuralNetworkFiles import Core

from sklearn.model_selection import KFold

bp = Blueprint("experiments", __name__, url_prefix="/experiments")


logger = logging.getLogger()

# should be modified to work with a db or class if necessary.
# Otherwise, the choices being pre-available on page load will slightly speed the process.


@bp.before_app_request
def load_possible_experiments():
    list_Algorithms = MLA.getMLAs()
    # list for preoptimization options
    list_Preopt_Categories = Preoptimization.getPreopt_Categories()
    list_Standardization = Standardization.getStandardization()
    # list for Neural Network options
    list_Layer_Categories = NeuralNetwork.getLayer_Categories()
    list_Core = Core.getCore()

    # ----------------Data Types-------------------------->
    g.data_types = ["Tabular", "Image", "Text", "Signal"]
    g.data_types_Name = ["Tabular", "Image", "Text", "Signal"]
    g.data_types_Info = [["Tabular is data that is displayed in columns or tables and does not pertain to the other data types."],
                         ["Image is data that is usually 3-dimentional corresponding to the three color spectrom, RGB"],
                         ["Text is data containing textual words or sentences."],
                         ["Signal is data containing time-series data corresponding to a signal format."]]
    g.Data_Types = zip(g.data_types, g.data_types_Name, g.data_types_Info)

    # ----------------new Cycon--------------------------->
    # First choice is between various categories of ML
    g.section_Method = ["MLA", "DLANN"]
    g.section_Method_Display_Name = [
        "Machine Learning Algorithm (MLA)", "Deep Learning Artifical Neural Networks (DLANN)"]
    g.section_Info = [["Machine learning algorithms are mathematical model mapping methods. They are used to learn patterns embedded in the existing training dataset in order to perform pattern recognition, classification, and prediction.\n\nCurrently, the only algorithms available on cycon is under the classification objective. Other objectives that will be added later include clustering and regression."],
                      ["DLANN info"]]
    g.Methodologies = zip(
        g.section_Method, g.section_Method_Display_Name, g.section_Info)

    # Obtain the selection of Algorithm Names and Definition.
    algorithm_Names = []
    algorithm_Definition = []
    algorithm_Names.append("")
    algorithm_Definition.append("")

    for algorithm in list_Algorithms:
        algorithm_Names.append(algorithm.getName())
        algorithm_Definition.append(algorithm.getDefinition())
    g.section_algorithm = algorithm_Names
    g.section_Info = algorithm_Definition
    g.Algorithms = zip(g.section_algorithm, g.section_Info)

    # ----------------Preoptimiztion-------------------------->
    # create list of options to choose a category of preoptimization options.
    preopt_Category_Names = []
    preopt_Category_Display_Names = []
    preopt_Category_Definition = []

    for preopt_Category in list_Preopt_Categories:
        preopt_Category_Names.append(preopt_Category.getName())
        preopt_Category_Display_Names.append(preopt_Category.getDisplayName())
        preopt_Category_Definition.append(preopt_Category.getDefinition())
    g.section_preopt_Category_Names = preopt_Category_Names
    g.section_preopt_Category_Display_Names = preopt_Category_Display_Names
    g.section_preopt_Category_Info = preopt_Category_Definition
    g.preopt_Categories = zip(g.section_preopt_Category_Names,
                              g.section_preopt_Category_Display_Names, g.section_preopt_Category_Info)

    # create list of options for the first category of preoprtimization (I.E. Standardization)
    preopt_Names = []
    preopt_Display_Names = []
    preopt_Definition = []

    for preopt in list_Standardization:
        preopt_Names.append(preopt.getName())
        preopt_Display_Names.append(preopt.getDisplayName())
        preopt_Definition.append(preopt.getDefinition())
    g.section_preopt_Names = preopt_Names
    g.section_preopt_Display_Names = preopt_Display_Names
    g.section_preopt_Info = preopt_Definition
    g.preopts = zip(g.section_preopt_Names,
                    g.section_preopt_Display_Names, g.section_preopt_Info)

    # -------------------Neural Network Layers----------------------->
    # create list of options to choose a category of layer options.
    layer_Category_Names = []
    layer_Category_Display_Names = []
    layer_Category_Definition = []

    for layer_Category in list_Layer_Categories:
        layer_Category_Names.append(layer_Category.getName())
        layer_Category_Display_Names.append(layer_Category.getDisplayName())
        layer_Category_Definition.append(layer_Category.getDefinition())
    g.layer_Category_Names = layer_Category_Names
    g.layer_Category_Display_Names = layer_Category_Display_Names
    g.layer_Category_Info = layer_Category_Definition
    g.NN_layer_Categories = zip(
        g.layer_Category_Names, g.layer_Category_Display_Names, g.layer_Category_Info)

    # create list of options for the first category of preoprtimization (I.E. Core)
    layer_Names = []
    layer_Display_Names = []
    layer_Definition = []

    for layer in list_Core:
        layer_Names.append(layer.getName())
        layer_Display_Names.append(layer.getDisplayName())
        layer_Definition.append(layer.getDefinition())
    g.layer_Names = layer_Names
    g.layer_Display_Names = layer_Display_Names
    g.layer_Info = layer_Definition
    g.layers = zip(g.layer_Names, g.layer_Display_Names, g.layer_Info)


@bp.route("/new_experiment")
def new_experiment():
    return render_template("experiments/new_experiment.html")


@bp.route("/lca", methods=["GET"])
def lca():
    user_id = session.get("user_id")
    logging.debug("=== Uploading files: %s", user_id)

    if user_id is None:
        g.user = None
        flash("You need to login to upload your datasets!")
        return redirect(url_for("auth.login"))
    else:
        try:
            manager = DBManager.instance(
                password_file=current_app.config["DB_PASSWORD"]
            )
            plan = manager.get_plan_by_user_id(user_id)
        except Error as e:
            logging.debug(f"=== Failed to get user plan: {e} ===")
            return redirect(url_for("auth.plans"))

        logging.debug("=== Upload plan: %s", plan)
        if plan is None:
            flash("You have not subscribed to a plan!")
            return redirect(url_for("auth.plans"))
        else:
            # if plan.get('tier') == 'free':
            # TODO check file size
            user_storage = plan.get("storage_url")
            base_folder = os.getcwd()
            upload_path = Path(base_folder+'/data/') / user_storage
            filenames = os.listdir(upload_path)
            files = []
            for filename in filenames:
                file_path = upload_path / filename
                with open(file_path) as file:
                    data = csv.reader(file)
                    content = [row for row in data]
                    files.append(dict(filename=filename, content=content))

            return render_template("experiments/lca.html", files=files)


@bp.route("/cycon")
def cycon():
    return render_template("experiments/cycon.html")


@bp.route("/calculate", methods=["POST"])
def calculate():
    processes_input = request.form.get("processes")
    choice = request.form.get("choice")
    user_data = dict()
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
        flash("You need to login to upload your datasets!")
        return redirect(url_for("auth.login"))
    else:
        try:
            manager = DBManager.instance(
                password_file=current_app.config["DB_PASSWORD"]
            )
            plan = manager.get_plan_by_user_id(user_id)
        except Error as e:
            logging.debug(f"=== Failed to get user plan: {e} ===")
        if plan is None:
            flash('You have not yet created a plan.j')
            return redirect(url_for("auth.plans"))
        else:
            user_storage = plan.get("storage_url")
            files_path = Path('data/') / user_storage
            files = [(f.name, f.absolute())
                        for f in list(files_path.glob("*"))]
            for (key, value) in files:
                logger.debug("=== file data: %s %s", key, value)
                user_data[key], error = read_data(value)
                if error:
                    return jsonify(error=error)

    # else:
    if not processes_input:
        return flash("Invalid arguments!")
    processes = json.loads(processes_input)
    # for key, value in request.files.items():
    #     logger.debug("=== file data: %s %s", key, value)
    #     data[key], error = read_data(value)
    #     if error:
    #         return jsonify(error=error)
    logger.debug("=== Equations: %s %s", processes)

    results = []
    num_process = 0
    for process in processes:
        num_process += 1
        filename = process.get("filename")
        kind = process.get("kind")
        data = None
        if not filename:
            error = f"Missing filename for process {num_process}"
            return jsonify(error=error)
        if kind == "csv":
            data = user_data.get(filename)
        else:
            file = request.files.get(filename)
            data, error = read_data(file)
            if error:
                return jsonify(error=error)
        process_data = data

        logger.debug("=== Process data: %s", data)
        if process_data is None:
            error = f"Missing csv file '{filename}' for process {num_process}"
            return jsonify(error=error)
        equation = process.get("equation")
        if not equation or equation == "":
            error = f"Missing equation for process for process {num_process}"
            return jsonify(error=error)
        name = process.get("name")
        logger.debug("=== Process %s: %s %s",
                     num_process, filename, process_data)
        calculator = Calculator()
        evaluated, result, formula = calculator.evaluate(
            equation=equation, data=process_data)
        logger.debug("=== Process %s Results: %s, %s %s",
                     num_process, evaluated, result, formula)
        if not evaluated:
            error = f"Error in the formula for process {num_process}\n{result}"
            return jsonify(error=error)

        sympy.init_printing(use_latex='mathjax')
        formula = latex(equation, mode="plain")
        output = dict(result=result, name=name, equation=formula)
        results.append(output)

    logger.debug("=== results: %s | dtype %s", results, type(results))
    return jsonify(processes=results)


@bp.route("/run_experiment", methods=["POST"])
def run_experiment():
    processes_input = request.form.get("processes")
    data = json.loads(processes_input)

    filename = request.form.get("csvFileName")
    csv_file = request.files.get("csvFile")

    data["csvFileName"] = filename
    data["csvFile"] = csv_file

    # Split
    if data['validation'] == "Split":
        status, msg, Metrics = Validation.Split(data)

    # K-Fold
    elif data['validation'] == "K-Fold":
        status, msg, Metrics = Validation.K_Fold(data)

    if status == "worked":
        # Open json file for the experiment.
        baseFolder = os.getcwd()
        locationSavedResults = Path(baseFolder) / "SavedResults"
        filename = secure_filename(data["projectName"] + ".json")
        filepath = locationSavedResults / filename.lower()
        if os.path.exists(filepath):
            os.remove(filepath)
            fp = open(filepath, "a")
        else:
            fp = open(filepath, "a")

        # write to json file
        metrics_Dump = json.dumps(Metrics)

        fp.write(metrics_Dump)

        # close the connection
        fp.close()

    Results = [status, msg, Metrics]

    return json.dumps(Results)


@bp.route("/getResults", methods=["POST"])
def getResults():
    output = request.get_json()
    formData = json.loads(output)

    data = formData['form']

    baseFolder = os.getcwd()
    locationSavedResults = Path(baseFolder) / "SavedResults"
    filename = data["projectName"] + ".json"
    filepath = locationSavedResults / filename.lower()
    fp = open(filepath, "r")

    Metrics = json.load(fp)

    # close the connection
    fp.close()

    return json.dumps(Metrics)


@bp.route("/getAlgorithmParameters", methods=["POST"])
def getAlgorithmParameters():
    output = request.get_json()
    data = json.loads(output)

    Parameters = MLA.getParameters(data["Algorithm"])

    return json.dumps(Parameters)


@bp.route("/getCategoryPreopts", methods=["POST"])
def getCategoryPreopts():
    output = request.get_json()
    data = json.loads(output)

    preopts = Preoptimization.getCategoryPreopts(data["Category"])

    return json.dumps(preopts)


@bp.route("/results")
def results():
    return render_template("experiments/results.html")


@bp.route("/getCSVResults", methods=["POST"])
def getCSVResults():
    processes_input = request.form.get("processes")
    data = json.loads(processes_input)

    filename = request.form.get("csvFileName")
    csv_file = request.files.get("csvFile")

    data["csvFileName"] = filename
    data["csvFile"] = csv_file

    status, msg, info = Preoptimization.getCSV_PDF(data)

    Results = [status, msg, info]

    return json.dumps(Results)


@bp.route("/downloadCSV", methods=["POST"])
def downloadCSV():
    processes_input = request.form.get("processes")
    data = json.loads(processes_input)

    filename = request.form.get("csvFileName")
    csv_file = request.files.get("csvFile")

    data["csvFileName"] = filename
    data["csvFile"] = csv_file

    status, msg, info = Preoptimization.downloadCSV(data)

    Results = [status, msg, info]

    return json.dumps(Results)


@bp.route("/getPreoptParameters", methods=["POST"])
def getPreoptParameters():
    output = request.get_json()
    data = json.loads(output)

    Parameters = Preoptimization.getParameters(data["Preopt"])

    return json.dumps(Parameters)


@bp.route("/getLayerParameters", methods=["POST"])
def getLayerParameters():
    output = request.get_json()
    data = json.loads(output)

    Parameters = NeuralNetwork.getParameters(data["Layer"])

    return json.dumps(Parameters)

# Gets the colummn names inside the csv.


@bp.route("/getCSVColumnTitles", methods=["POST"])
def getCSVColumnTitles():
    filename = request.form.get("csvFileName")
    csv_file = request.files.get("csvFile")

    data = {"csvFileName": filename, "csvFile": csv_file}

    columnTitles = Preoptimization.getCSVColumnTitles(data)

    return json.dumps(columnTitles)
