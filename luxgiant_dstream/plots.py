"""
Module with function for drawing plots

The module provides functions to draw manhattan and qq plots for GWAS data.

Functions:
----------
manhattan_plot(df_gwas:pd.DataFrame, plots_dir:str, df_annot:pd.DataFrame=None, annotate:bool=False)->bool
    Draw a manhattan plot for GWAS data.
qq_plot(df_gwas:pd.DataFrame, plots_dir:str)->bool
    Draw a qq plot for GWAS data.

The function qq_plot is a Python implementation of the R code provided in the following links: https://gist.github.com/MrFlick/10477946 or here https://github.com/hakyimlab/IntroStatGen/blob/master/gists/qqunif.r

"""

import os

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats

from matplotlib.axes import Axes

from adjustText import adjust_text

def manhattan_plot(df_gwas:pd.DataFrame, plots_dir:str=None, df_annot:pd.DataFrame=None, annotate:bool=False)->bool:

    """
    Function to draw a manhattan plot for GWAS data.
    
    Parameters:
    -----------
    df_gwas : pd.DataFrame
        Dataframe with GWAS summary statistics.
    plots_dir : str
        Path to the directory to save the plot.
    df_annot : pd.DataFrame (default=None)
        Dataframe with annotation information for SNPs of interest.
    annotate : bool (default=False)
        Whether to annotate the plot with gene names.

    Returns:
    --------
    bool
    """
    
    # keep columns of interest
    df = df_gwas.copy()
    df['log10P'] = -np.log10(df['p'])

    # sort values by chromosome
    df = df.sort_values('CHR')

    # to get colors by chromosome
    df['ind'] = range(len(df))
    df_grouped = df.groupby(('CHR'))

    # Subset dataframe to highlight specific SNPs
    if df_annot is not None:
        snps = df_annot['SNP'].to_list()
        genes = df_annot['GENE'].to_list()
        highlighted_snps = df[df['SNP'].isin(snps)]  # Filter for the SNPs of interest

    # Set the figure size
    fig = plt.figure(figsize=(50, 25))
    ax = fig.add_subplot(111)

    if df_annot is not None:
        ax = draw_chrom_groups(ax, df_grouped, highlighted_snps)
    else:
        ax = draw_chrom_groups(ax, df_grouped, None)

    if annotate:
        # Add gene names to highlighted SNPs
        ax = annotate_plot(ax, highlighted_snps, genes)

    # Set axis limits
    ax.set_xlim([0, len(df)])
    ax.set_ylim([0, max(df['log10P']) + 1])

    # Add horizontal line for genome-wide significance threshold (-log10(5e-8))
    ax.axhline(y=-np.log10(5e-8), color='blue', linestyle='--', linewidth=1)

    # Add labels and title
    ax.set_xlabel('Chromosome', fontsize=24)  # Adjust fontsize as needed
    ax.set_ylabel('-log10(P-value)', fontsize=24)  # Adjust fontsize as needed
    ax.set_title('Manhattan Plot', fontsize=30)  # Add a title if needed

    # Customize the grid
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    if plots_dir is None:
        return ax
    else:
        # Display the plot
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'manhattan_plot.png'))

        return True
    
def draw_chrom_groups(ax:Axes, df_chr_group, highlighted_snps:pd.DataFrame)->Axes:

    # Colors for alternating chromosomes
    colors = ['grey', 'skyblue']

    # Variables to store labels and positions for the x-axis
    x_labels = []
    x_labels_pos = []

    # Loop over each group by chromosome
    for num, (name, group) in enumerate(df_chr_group):

        # Plot each chromosome with alternating colors
        ax.scatter(group['ind'], group['log10P'], color=colors[num % len(colors)], s=10)

        # Add chromosome label and its position
        x_labels.append(name)
        middle_pos = (group['ind'].iloc[-1] + group['ind'].iloc[0]) / 2
        x_labels_pos.append(middle_pos)

        # Set the x-axis labels and positions
        ax.set_xticks(x_labels_pos)
        ax.set_xticklabels(x_labels, fontsize=20)  # Adjust fontsize as needed

        if highlighted_snps is not None:
            # Plot highlighted SNPs with a different color (red) and larger point size
            ax.scatter(highlighted_snps['ind'], highlighted_snps['log10P'], color='red', s=50, label='Highlighted SNPs')

    return ax

def annotate_plot(ax:Axes, highlighted_snps:pd.DataFrame, snps:list, genes:list)->Axes:

    texts = []  # A list to store text annotations for adjustment
    for i, row in highlighted_snps.iterrows():
        gene = genes[snps.index(row['SNP'])]  # Get corresponding gene name
        # Add text label to the SNP
        text = ax.text(row['ind'], row['log10P'], gene, fontsize=12, ha='right', va='bottom', color='black',
                       bbox=dict(boxstyle='round,pad=0.3', edgecolor='black', facecolor='white'))
        texts.append(text)
    # Adjust the text to prevent overlaps using adjustText
    adjust_text(texts, arrowprops=dict(arrowstyle='-', color='black'))

    return ax

def qq_plot(df_gwas:pd.DataFrame, plots_dir:str)->bool:

    """
    Function to draw a qq plot for GWAS data.

    Parameters:
    -----------
    df_gwas : pd.DataFrame
        Dataframe with GWAS summary statistics.
    plots_dir : str
        Path to the directory to save the plot.

    Returns:
    --------
    bool
    """
    
    pvalues = df_gwas['p'].values
    grp = None
    n = len(pvalues)

    log_p = -np.log10(pvalues)
    exp_x = -np.log10((stats.rankdata(pvalues, method='ordinal') - 0.5) / n)

    if grp is not None:

        # Create a DataFrame with rounded pvalues and exp_x, and grp
        thin = pd.DataFrame({
            'pvalues': np.round(log_p, 3),
            'exp_x': np.round(exp_x, 3),
            'grp': grp
        }).drop_duplicates()

        # Assign the updated group after thinning
        grp = thin['grp'].values
    else:

        # Create a DataFrame with rounded pvalues and exp_x
        thin = pd.DataFrame({
            'pvalues': np.round(log_p, 3),
            'exp_x': np.round(exp_x, 3)
        }).drop_duplicates()

    # Update pvalues and exp_x after thinning
    log_p = thin['pvalues'].values
    exp_x = thin['exp_x'].values

    axis_range =  [float(min(log_p.min(), exp_x.min()))-0.5, float(max(log_p.max(), exp_x.max()))+1]

    fig, ax = plt.subplots(figsize=(10,10))

    # Calculate the confidence intervals if draw_conf is True
    def plot_confidence_interval(n:int, conf_points:int=1500, conf_col:str="lightgray", conf_alpha:float=0.05)->None:

        """
        Function to plot the confidence interval for the QQ plot.

        Parameters:
        -----------
        n : int
            Number of p-values.
        conf_points : int (default=1500)
            Number of points to plot the confidence interval.
        conf_col : str (default="lightgray")
            Color of the confidence interval.
        conf_alpha : float (default=0.05)
            Alpha value for the confidence interval.

        Returns:
        --------
        None
        """
        
        conf_points = min(conf_points, n - 1)
        mpts = np.zeros((conf_points * 2, 2))

        for i in range(1, conf_points + 1):

            x = -np.log10((i - 0.5) / n)

            y_upper = -np.log10(stats.beta.ppf(1 - conf_alpha / 2, i, n - i))
            y_lower = -np.log10(stats.beta.ppf(conf_alpha / 2, i, n - i))

            mpts[i - 1, 0] = x
            mpts[i - 1, 1] = y_upper
            mpts[conf_points * 2 - i, 0] = x
            mpts[conf_points * 2 - i, 1] = y_lower

        # Plot the confidence interval as a filled polygon
        plt.fill(mpts[:, 0], mpts[:, 1], color=conf_col)
        pass

    plot_confidence_interval(n, conf_points=1500, conf_col="lightgray", conf_alpha=0.05)

    if grp is not None:
        unique_groups = np.unique(grp)
        for group in unique_groups:
            group_mask = (grp == group)
            ax.scatter(exp_x[group_mask], log_p[group_mask], label=f'Group {group}', marker='o')
    else:
        ax.scatter(exp_x, log_p, marker='o')

    # Line y = x
    ax.plot(axis_range, axis_range, color='red', linestyle='--', lw=1)

    ax.set_xlim(axis_range)
    ax.set_ylim(axis_range)

    ax.set_xlabel('Expected (-log10 p-value)')
    ax.set_ylabel('Observed (-log10 p-value)')
    ax.set_aspect('equal')
    ax.grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'qq_plot.png'))

    return True

def miami_plot(df_gwas_top:pd.DataFrame, df_gwas_bottom:pd.DataFrame, plots_dir:str, df_top_annot:pd.DataFrame=None, df_bottom_annot:pd.DataFrame=None)->bool:

    """
    Function to draw a Miami plot for GWAS data.

    Parameters:
    -----------
    df_gwas_top : pd.DataFrame
        Dataframe with GWAS results for top part of the plot.
    df_gwas_all : pd.DataFrame
        Dataframe with GWAS results for bottom part of the plot.
    plots_dir : str
        Path to the directory to save the plot.

    Returns:
    --------
    bool
    """
    
    # Set the figure size
    fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={'height_ratios': [1, 1]})

    ax[0] = manhattan_plot(df_gwas_top, annotate=False)
    ax[0].set_ylabel('-log10(p) (Your Results)')
    ax[0].set_title('Miami Plot: Your Results vs Known Results')

    ax[1] = manhattan_plot(df_gwas_bottom, annotate=False)
    ax[1].invert_yaxis()  # Invert the y-axis for the Miami plot effect
    ax[1].set_ylabel('-log10(p) (Known Results)')

    plt.tight_layout()

    plt.savefig(os.path.join(plots_dir, 'miami_plot.png'))
    plt.show()

    pass
