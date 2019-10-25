from typing import Optional, Union, Dict

import click
import numpy as np
import pandas as pd


class SurveyDesignSpec:
    """
    Holds parameters for building a statsmodels SurveyDesign object

    Parameters
    ----------
    survey_df: pd.DataFrame
        A DataFrame containing Cluster, Strata, and/or weights data
    strata: string or None
        The name of the strata variable in the survey_df
    cluster: string or None
        The name of the cluster variable in the survey_df
    nest: bool, default False
        Whether or not the clusters are nested in the strata (The same cluster IDs are repeated in different strata)
    weights: string or dictionary(string:string)
        The name of the weights variable in the survey_df, or a dictionary mapping variable names to weight names
    fpc: string or None
        The name of the variable in the survey_df that contains the finite population correction information.
        This reduces variance when a substantial portion of the population is sampled.
        May be specified as the total population size, or the fraction of the population that was sampled.
    single_cluster: str
        Setting controlling variance calculation in single-cluster ('lonely psu') strata
        'error': default, throw an error
        'scaled': use the average value of other strata
        'centered': use the average of all observations
        'certainty': that strata doesn't contribute to the variance

    Attributes
    ----------

    Examples
    --------
    >>> import clarite
    >>> clarite.analyze.SurveyDesignSpec(survey_df=survey_design_replication,
                                         strata="SDMVSTRA",
                                         cluster="SDMVPSU",
                                         nest=True,
                                         weights=weights_replication,
                                         fpc=None,
                                         single_cluster='scaled')
    """
    def __init__(self,
                 survey_df: pd.DataFrame,
                 strata: Optional[str] = None,
                 cluster: Optional[str] = None,
                 nest: bool = False,
                 weights: Union[str, Dict[str, str]] = None,
                 fpc: Optional[str] = None,
                 single_cluster: Optional[str] = 'error'):

        # Validate index
        if isinstance(survey_df.index, pd.core.index.MultiIndex):
            raise ValueError("survey_df: DataFrame must not have a multiindex")
        survey_df.index.name = "ID"

        # Store parameters
        self.survey_df = survey_df
        self.nest = nest

        # Defaults
        # Strata
        self.strata = None
        self.strata_name = None
        self.has_strata = False
        # Cluster
        self.cluster = None
        self.cluster_name = None
        self.has_cluster = False
        # Weight
        self.weights = None
        self.weight_names = None
        self.weight_name = None
        self.single_weight = False
        self.multi_weight = False
        # FPC
        self.fpc = None
        self.fpc_name = None
        self.has_fpc = False

        # Load Strata
        if strata is not None:
            self.strata_name = strata
            self.has_strata = True
            if self.strata_name not in self.survey_df:
                raise KeyError(f"strata key ('{self.strata_name}') was not found in the survey_df")
            else:
                self.strata = self.survey_df[self.strata_name]

        # Load Clusters (PSUs)
        if cluster is not None:
            self.cluster_name = cluster
            self.has_cluster = True
            if self.cluster_name not in self.survey_df:
                raise KeyError(f"cluster key ('{self.cluster_name}') was not found in the survey_df")
            else:
                self.cluster = self.survey_df[self.cluster_name]

        # Load FPC
        if fpc is not None:
            self.fpc_name = fpc
            self.has_fpc = True
            if self.fpc_name not in self.survey_df:
                raise KeyError(f"fpc key ('{self.fpc_name}') was not found in the survey_df")
            else:
                self.fpc = self.survey_df[self.fpc_name]

        # Load Weights
        if weights is not None:
            if type(weights) == dict:
                self.multi_weight = True
                self.weight_names = weights
                self.weights = dict()
                for var_name, weight_name in weights.items():
                    if weight_name not in self.survey_df:
                        raise KeyError(f"weights key for '{var_name}' ('{weight_name}') was not found in the survey_df")
                    else:
                        self.weights[var_name] = self.survey_df[weight_name]
            elif type(weights) == str:
                self.single_weight = True
                self.weight_name = weights
                if self.weight_name not in self.survey_df:
                    raise KeyError(f"the weight ('{self.weight_name}') was not found in the survey_df")
                else:
                    self.weights = self.survey_df[self.weight_name]

        # Load single_cluster
        if single_cluster not in {'error', 'scaled', 'certainty', 'centered'}:
            raise ValueError(f"if provided, 'single_cluster' must be one of "
                             f"'error', 'scaled', 'certainty', or 'centered'.")
        else:
            self.single_cluster = single_cluster

    def get_survey_design(self, regression_variable: Optional[str] = None, index: Optional[pd.Index] = None):
        """
        Build a survey design based on the regression variable

        Parameters
        ----------
        regression_variable : str or None
            Name of the variable being regressed.  Required if weights are variable-specific.
        index : pd.Index or None
            Data being used in the analysis whose index is a subset of the survey design indicies

        Returns
        -------
        survey_design: SurveyDesign
            SurveyDesign object used for further analysis
        index: pd.Index
            Index corresponding to all data in the design- limited by the input index or weights that are na or zero
        """
        # Return all observations if a subset index is not specified
        if index is None:
            index = self.survey_df.index

        # Get weights array
        if self.single_weight:
            weights = self.weights.loc[index]
        elif self.multi_weight:
            if regression_variable is None:
                raise ValueError("This SurveyDesignSpec uses variable-specific weights- "
                                 "a variable name is required to create a SurveyDesign object.")
            elif regression_variable not in self.weight_names:
                raise KeyError(f"The regression variable ({regression_variable}) "
                               f"was not found in the SurveyDesignSpec")
            else:
                weights = self.weights[regression_variable].loc[index]
        else:
            weights = None

        # Update index to remove missing, negative, or zero weights
        if weights is not None:
            weights = weights[~weights.isna() & (weights > 0)]
            n_removed = len(index) - len(weights)
            if n_removed > 0:
                click.echo(click.style(f"WARNING: {regression_variable} - {n_removed} observation(s) "
                                       f"with missing, negative, or zero weights were removed", fg='yellow'))
                index = weights.index

        # Get strata array
        if self.has_strata:
            strata = self.strata.loc[index]
        else:
            strata = None

        # Get cluster array
        if self.has_cluster:
            cluster = self.cluster.loc[index]
        else:
            cluster = None

        # Get fpc array
        if self.has_fpc:
            fpc = self.fpc.loc[index]
        else:
            fpc = None

        return SurveyDesign(strata=strata, cluster=cluster, weights=weights, fpc=fpc,
                            nest=self.nest, single_cluster=self.single_cluster), index


class SurveyDesign(object):
    """
    Description of a survey design

    Parameters
    -------
    strata : array-like or None
        Strata for each observation. If none, an array
        of ones is constructed
    cluster : array-like or None
        Cluster for each observation. If none, an array
        of ones is constructed
    weights : array-like or None
        The weight for each observation. If none, an array
        of ones is constructed
    fpc : ps.Series or None
        The finite population correction for each observation.
        If none, an array of zeros is constructed.
        If < 1, treated as sampling weights and use directly
        Otherwise, treat as cluster population size and convert to sampling weights as (number of obs in cluster) / fpc
    nest : boolean
        allows user to specify if PSU's with the same
        PSU number in different strata are treated as distinct PSUs.
    single_cluster : str
        Setting controlling variance calculation in single-cluster strata
        'error': default, throw an error
        'scaled': use the average value of other strata
        'centered': use the average of all observations
        'certainty': that strata doesn't contribute to the variance

    Attributes
    ----------
    weights : (n, ) pd.Series
        The weight for each observation
    n_strat : integer
        The number of district strata
    clust : (n, ) pd.Series
        The relabeled cluster array from 0, 1, ..
    strat : (n, ) pd.Series
        The related strata array from 0, 1, ...
    clust_per_strat : (self.n_strat, ) array
        Holds the number of clusters in each stratum
    strat_for_clust : ndarray
        The stratum for each cluster
    n_strat: integer
        The total number of strata
    n_clust : integer
        The total number of clusters across strata
    strat_names : list[str]
        The names of strata
    clust_names : list[str]
        The names of clusters
    """

    def __init__(self,
                 strata: Optional[pd.Series] = None,
                 cluster: Optional[pd.Series] = None,
                 weights: Optional[pd.Series] = None,
                 fpc: Optional[pd.Series] = None,
                 nest: bool = True,
                 single_cluster: str = 'error'):

        # Record inputs
        # Note: Currently allowed combinations of parameters:
        #        * Strata, Clusters (weights assumed to be 1)
        #        * Strata, Clusters, Weight
        # Note: Not Currently allowed combinations of parameters:
        #        * FPC (not allowed to be provided- further testing and documentation needed)
        #        * Weight only (further testing needed to confirm correctness)
        #        * Strata or Clusters (not both) - requires further testing
        self.has_strata = False
        self.has_clusters = False
        self.has_weight = False
        self.has_fpc = False
        if strata is not None:
            self.has_strata = True
        if cluster is not None:
            self.has_clusters = True
        if weights is not None:
            self.has_weights = True
        if fpc is not None:
            self.has_fpc = True

        strata, cluster, self.weights, self.fpc = self._check_args(strata, cluster, weights, fpc)

        # If requested, recode the PSUs to be sure that the same PSU # in
        # different strata are treated as distinct PSUs. This is the same
        # as the nest option in R.
        if nest:
            cluster = strata.astype(str) + "-" + cluster.astype(str)

        # Make strata and cluster into categoricals
        self.strat = strata.astype('category').rename('strat')
        self.clust = cluster.astype('category').rename('clust')

        # Get a combined dataframe to map the relationships
        combined = pd.concat([self.strat, self.clust, self.fpc], axis=1)

        # The number of clusters per stratum
        self.clust_per_strat = combined.groupby('strat')['clust'].nunique()

        # The stratum for each cluster
        self.strat_for_clust = combined.groupby('clust')['strat'].unique().apply(lambda l: l[0])

        # The fpc for each cluster
        self.fpc = combined.groupby('clust')['fpc'].unique().apply(lambda l: l[0])

        # Clusters within each stratum
        self.ii = combined.groupby('strat')['clust'].unique()

        # Record names
        self.strat_names = self.strat.cat.categories
        self.clust_names = self.clust.cat.categories

        # Record number of strat/clust
        self.n_strat = len(self.strat_names)
        self.n_clust = len(self.clust_names)

        # Record single cluster setting
        self.single_cluster = single_cluster

    def __str__(self):
        """
        The __str__ method for our data
        """
        summary_list = ["Number of observations: ", str(len(self.strat)),
                        "Sum of weights: ", str(self.weights.sum()),
                        "Number of strata: ", str(self.n_strat),
                        "Clusters per stratum: ", str(self.clust_per_strat)]

        return "\n".join(summary_list)

    def _check_args(self,
                    strata: Optional[pd.Series] = None,
                    cluster: Optional[pd.Series] = None,
                    weights: Optional[pd.Series] = None,
                    fpc: Optional[pd.Series] = None):
        """
        Minor error checking to make sure user supplied any of
        strata, cluster, or weights.

        Parameters
        ----------
        strata : pd.Series or None
            Strata for each observation. If none, an array
            of ones is constructed
        cluster : pd.Series or None
            Cluster for each observation. If none, an array
            of sequential values is constructed
        weights : pd.Series or None
            The weight for each observation. If none, an array
            of ones is constructed
        fpc: pd.Series or None
            The finite population correction for each observation.
            If none, an array of zeros is constructed.
            If < 1, treated as sampling weights and use directly
            Otherwise, treat as strata population size and convert to sampling weights as (number of obs in strata)/fpc

        Returns
        -------
        strata : ndarray
            Series of the strata labels
        cluster : ndarray
            Series of the cluster labels
        weights : ndarray
            Series of the observation weights
        fpc: pd.Series
            Series of fpc values
        """
        # At least one must be defined
        if all([x is None for x in (strata, cluster, weights)]):
            raise ValueError("""At least one of strata, cluster, rep_weights, and weights
                             must not be None""")

        # Get corrected index information for creating replacements for None
        index = [x.index for x in (strata, cluster, weights) if x is not None][0]
        n = len(index)

        # Make sure index is equal for all given parameters
        if not all([index.equals(x.index) for x in (strata, cluster, weights) if x is not None]):
            raise ValueError("""index of strata, cluster, and weights are not all compatible""")

        # Create default values or update name of given value
        if strata is None:
            strata = pd.Series(np.ones(n), index=index, name='strata')
        else:
            strata = strata.rename('strata')
        if cluster is None:
            cluster = pd.Series(np.arange(n), index=index, name='cluster')
        else:
            cluster = cluster.rename('cluster')
        if weights is None:
            weights = pd.Series(np.ones(n), index=index, name='weights')
        else:
            weights = weights.rename('weights')
        if fpc is None:
            fpc = pd.Series(np.zeros(n), index=index, name='fpc')
        else:
            fpc = fpc.rename('fpc')
            if not all(fpc <= 1):
                # Assume these are actual population size, and convert to a fraction
                if self.has_strata:
                    # Divide the sampled strata size by the fpc
                    combined = pd.merge(strata, fpc, left_index=True, right_index=True)
                    sampled_strata_size = combined.groupby('strata')['fpc'].transform('size')
                    fpc = sampled_strata_size/fpc
                elif self.has_clusters and not self.has_strata:
                    # Clustered sampling: Divide sampled clusters by the fpc
                    sampled_cluster_size = len(cluster.unique())
                    fpc = sampled_cluster_size/fpc
                try:
                    assert all((fpc >= 0) & (fpc <= 1))
                except AssertionError:
                    raise ValueError("Error processing FPC- invalid values")
        return strata, cluster, weights, fpc

    def get_jackknife_rep_weights(self, dropped_clust):
        """
        Computes 'delete 1' jackknife replicate weights

        Parameters
        ----------
        dropped_clust : string
            Which cluster to leave out when computing 'delete 1' jackknife replicate weights

        Returns
        -------
        w : ndarray
            Augmented weight
        """
        # get stratum that the cluster belongs in
        s = self.strat_for_clust[dropped_clust]
        nh = self.clust_per_strat[s]
        w = self.weights.copy()
        # all weights within the stratum are modified
        w[self.strat == s] *= nh / float(nh - 1)
        # but if you're within the cluster to be removed, set as 0
        w[self.clust == dropped_clust] = 0
        return w

    def get_dof(self, X):
        """
        Calculate degrees of freedom based on a subset of the design

        Parameters
        ----------
        X : pd.DataFrame
            Input data used in the calculation

        Returns
        -------
        dof : int
            Degrees of freedom
        """
        # num of clusters minus num of strata minus (num of predictors - 1)
        return self.clust.loc[X.index].nunique() - self.strat.loc[X.index].nunique() - (X.shape[1] - 1)
