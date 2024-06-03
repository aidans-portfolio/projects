
# This script was created for my MSFA practicum project
# In a nutshell, this program does the following:
# - Ask for user parameters, including research key word and number of authors to load into dataframe
# - Using above parameters, use OpenAlex API to get top authors related to research keyword
# - Acquire number of key metrics about authors, such as number of published works and number of citations
# - Use metrics to calculate pseudo "Q" score from provided partner company research paper
# - Plot data visually to allow partner company to quickly access relevant information

#pip install pyalex
#needed if first time running

## Import necessary packages: pandas, pyalex, matplotlib, numpy
from pyalex import Works, Authors, Sources, Institutions, Concepts, Publishers

import pandas as pd

import matplotlib.pyplot as plt

import numpy as np


###################################################   get user inputs   ###################################################

#Get the research industry you are looking into and # of works to lookup
keyword_search = input("keyword: ").lower()


number_search = int(input("number of authors: "))

print(keyword_search)
print(number_search)


###################################################   scrape dataframes   ###################################################

#creates a page from OpenAlex with #number_search amount of works related to keyword_search

pager = Works().search(keyword_search).paginate(per_page=50)

#create empty DF to collect authors name and id
authorsDF = pd.DataFrame({'id':[], 'name':[]})

##fill authorsDF with unique list of names and ids
#also limits # of authors with number_search

first_time = 0
for page in pager:
    for work in page:
        authors = dict(work)['authorships']
        for author in authors:
            author_dict = author['author']
            new_row = {'id':author_dict['id'], 'name':author_dict['display_name']}
            if first_time==0:
                authorsDF=pd.concat([authorsDF,pd.DataFrame([new_row])],ignore_index=True)
                first_time+=1
            elif len(authorsDF) < number_search:
                if authorsDF['id'].str.contains(new_row['id']).any():
                    pass
                else:
                    authorsDF=pd.concat([authorsDF,pd.DataFrame([new_row])],ignore_index=True)
            else: 
                break
    if len(authorsDF)==number_search:
        break
    else:
        pass
        



#list of author IDs to iterate through later
author_id_list = authorsDF.loc[:,'id']

#empty DF to collect stats on authors
authorStatDF = pd.DataFrame({'id':[], 'works_count':[], 'cited_by_count':[], '2yr_mean_citedness':[],
                          'h_index':[], 'i10_index':[]})




#get each author statistics
#gets works_count, cited_by_count, 2yr_mean_citedness, h_index, i10_index
#careful, takes about 3-5 minutes to run for ~520 elements
for au_id in author_id_list:
    try:
        auth_dict = dict(Authors()[au_id])
    except:
        continue
    else:
        new_row = {'id':auth_dict['id'], 'works_count':auth_dict['works_count'], 'cited_by_count':auth_dict['cited_by_count'],
              '2yr_mean_citedness':auth_dict['summary_stats']['2yr_mean_citedness'],
               'h_index':auth_dict['summary_stats']['h_index'], 'i10_index':auth_dict['summary_stats']['i10_index']}
        authorStatDF=pd.concat([authorStatDF,pd.DataFrame([new_row])],ignore_index=True)
    

###################################################   transform dataframes   ###############################################

#merge authorsDF and authorStatDF into a final_authorDF
final_authorDF = authorStatDF.merge(authorsDF, on='id', how='left')

#create calculated column (will become pseudo Q score) - can change this equation to change plot below
final_authorDF['calculated'] = np.exp(np.log(final_authorDF['i10_index']) - final_authorDF['2yr_mean_citedness'])


#rename DF so easier to work with
df = final_authorDF

#create rank column for calculated column
#will be used to create color column later
df['rank'] = df['calculated'].rank(method='dense', ascending=False)

#function to create new column using rank in order to color by top 20%, mid 60%,
# and bottom 20%
def sort_ranks(rank_num):
    top_20 = len(df)*0.2
    top_80 = len(df)*0.8
    if rank_num <= top_20:
        return 'top20%'
    elif rank_num > top_20 and rank_num <= top_80:
        return 'mid60%'
    else:
        return 'bottom20%'

#create colors column with above function
df['colors'] = df['rank'].apply(sort_ranks)


###################################################   plot data   #######################################################

#determine plot axes
x = df['calculated'].values
y = df['h_index'].values

#create basic plot without data
fig, ax = plt.subplots()

#create color dictionary, can change to change colors on plot
color_dict = {'top20%':'red', 'mid60%':'green', 'bottom20%':'blue'}

#initialize scatterplot using axes and colors above
sc = plt.scatter(x, np.log(y), c=df.colors.map(color_dict))

#create empty annotation, will be utilized by update_annot and hover functions below
annot = ax.annotate("", xy=(0, 0), xytext=(-50, 10), textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="w"),
                    arrowprops=dict(arrowstyle="->"))
annot.set_visible(False)


#function to update annotation using position of cursor on plot
#currently updates annotation to the name of the author but can be any part of the dataframe
#set text variable to what you want the hover annotation to display
def update_annot(ind):
    pos = sc.get_offsets()[ind["ind"][0]]
    annot.xy = pos
    text = "Name: {}".format(df.loc[ind["ind"][0], 'name'])
    annot.set_text(text)
    annot.get_bbox_patch().set_alpha(0.4)

#function to check whether cursor is over the plot, and to update the annotation if
#the cursor moves over a point on the scatterplot
#and to hide it if the cursor moves away from the points
def hover(event):
    vis = annot.get_visible()
    if event.inaxes == ax:
        cont, ind = sc.contains(event)
        if cont:
            update_annot(ind)
            annot.set_visible(True)
            fig.canvas.draw_idle()
        else:
            if vis:
                annot.set_visible(False)
                fig.canvas.draw_idle()

#use matplotlib event abilities to detect cursor movement
fig.canvas.mpl_connect("motion_notify_event", hover)

#create the labels and title of the plot
plt.xlabel("Psuedo Q score equation")
plt.ylabel("log of h-index")
plt.title("Psuedo Q score chart for: " + keyword_search)

#import few extras from matplotlib needed for separate legend
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

#create separate legend to describe colors, needs to be updated separately from the colors_dict above
legend_elements = [Line2D([0], [0], marker='.', color='red', label='Top 20%',
                          markerfacecolor='red', markersize=15),
                   Line2D([0], [0], marker='.', color='green', label='Middle 60%',
                          markerfacecolor='green', markersize=15),
                  Line2D([0], [0], marker='.', color='blue', label='Bottom 20%',
                          markerfacecolor='blue', markersize=15),]

#set legend in upper left corner
ax.legend(handles=legend_elements, loc='upper left')

#display the plot
plt.show()


