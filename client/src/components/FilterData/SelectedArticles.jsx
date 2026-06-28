import { useState, useEffect } from 'react';
import axios from 'axios';
import Plot from '../Plot';
import moment from 'moment';

const SelectedArticles = ({ selectedRows, project }) => {
    const [articleData, setArticleData] = useState([]);
    const [pageViewsData, setPageViewsData] = useState([]);

    useEffect(() => {
        // Fetch data for all selected articles when selectedRows change
        if (Array.isArray(selectedRows) && selectedRows.length > 0) {
            fetchAllArticlesData(selectedRows);
        } else {
            setArticleData([]);
            setPageViewsData([]);
        }
        // fetchAllArticlesData is stable for the lifetime of this component and
        // only needs to run when the selected rows change.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedRows]);

    const fetchAllArticlesData = (articles) => {
        const articlePromises = articles.map(article => 
            axios.get(`/get_article_data?project=${project}&page_id=${article.page_id}`)
        );

        Promise.all(articlePromises)
            .then(responses => {
                const allArticleData = responses.map(response => response.data);
                const aggregatedArticleData = aggregateArticleData(allArticleData);
                setArticleData(aggregatedArticleData);

                // Fetch page views data for the aggregated article data
                const titles = articles.map(article => article.page_title);
                const start = aggregatedArticleData[0]?.month.replace('-', '') + '01';
                const end = aggregatedArticleData[aggregatedArticleData.length - 1]?.month.replace('-', '') + '01';
                if (start && end) {
                    fetchPageViewsData(titles, start, end);
                }
            })
            .catch(error => {
                console.error('Error fetching article data:', error);
            });
    };

    const fetchPageViewsData = (titles, start, end) => {
        const pageViewsPromises = titles.map(title =>
            axios.get(`/get_pageviews?title=${encodeURIComponent(title)}&start=${start}&end=${end}`)
        );

        Promise.all(pageViewsPromises)
            .then(responses => {
                const allPageViewsData = responses.flatMap(response => response.data.items);
                const aggregatedPageViewsData = aggregatePageViewsData(allPageViewsData);
                setPageViewsData(aggregatedPageViewsData);
            })
            .catch(error => {
                console.error('Error fetching page views data:', error);
            });
    };

    const aggregateArticleData = (allArticleData) => {
        const aggregatedData = {};
        allArticleData.forEach(articleData => {
            articleData.forEach(dataPoint => {
                if (!aggregatedData[dataPoint.month]) {
                    aggregatedData[dataPoint.month] = {
                        month: dataPoint.month,
                        pred_qual: 0,
                        num_refs: 0,
                        num_media: 0,
                        num_wikilinks: 0,
                        num_categories: 0,
                        num_headings: 0,
                        page_length: 0,
                        pred_qual_sum: 0,
                        num_refs_sum: 0,
                        num_media_sum: 0,
                        num_wikilinks_sum: 0,
                        num_categories_sum: 0,
                        num_headings_sum: 0,
                        page_length_sum: 0,
                        count: 0
                    };
                }
                aggregatedData[dataPoint.month].pred_qual += dataPoint.pred_qual;
                aggregatedData[dataPoint.month].num_refs += dataPoint.num_refs;
                aggregatedData[dataPoint.month].num_media += dataPoint.num_media;
                aggregatedData[dataPoint.month].num_wikilinks += dataPoint.num_wikilinks;
                aggregatedData[dataPoint.month].num_categories += dataPoint.num_categories;
                aggregatedData[dataPoint.month].num_headings += dataPoint.num_headings;
                aggregatedData[dataPoint.month].page_length += dataPoint.page_length;

                // Sum
                aggregatedData[dataPoint.month].pred_qual_sum += dataPoint.pred_qual;
                aggregatedData[dataPoint.month].num_refs_sum += dataPoint.num_refs;
                aggregatedData[dataPoint.month].num_media_sum += dataPoint.num_media;
                aggregatedData[dataPoint.month].num_wikilinks_sum += dataPoint.num_wikilinks;
                aggregatedData[dataPoint.month].num_categories_sum += dataPoint.num_categories;
                aggregatedData[dataPoint.month].num_headings_sum += dataPoint.num_headings;
                aggregatedData[dataPoint.month].page_length_sum += dataPoint.page_length;

                aggregatedData[dataPoint.month].count += 1;
            });
        });
        return Object.values(aggregatedData).map(data => ({
            month: data.month,
            pred_qual: data.pred_qual / data.count,
            num_refs: data.num_refs / data.count,
            num_media: data.num_media / data.count,
            num_wikilinks: data.num_wikilinks / data.count,
            num_categories: data.num_categories / data.count,
            num_headings: data.num_headings / data.count,
            page_length: data.page_length / data.count,
            pred_qual_sum: data.pred_qual_sum,
            num_refs_sum: data.num_refs_sum,
            num_media_sum: data.num_media_sum,
            num_wikilinks_sum: data.num_wikilinks_sum,
            num_categories_sum: data.num_categories_sum,
            num_headings_sum: data.num_headings_sum,
            page_length_sum: data.page_length_sum,
        }));
    };

    const aggregatePageViewsData = (allPageViewsData) => {
        const monthlyData = allPageViewsData.reduce((acc, item) => {
            const month = moment(item.timestamp, "YYYYMMDDHH").format("YYYY-MM");
            if (!acc[month]) {
                acc[month] = 0;
            }
            acc[month] += item.views;
            return acc;
        }, {});

        return Object.keys(monthlyData).map(month => ({
            month,
            views: monthlyData[month]
        }));
    };

    const downloadCSV = () => {
        const articleTitles = Array.isArray(selectedRows) ? selectedRows.map(article => article.page_title) : [];
        axios.post(`/download_csv?project=${project}`, articleTitles)
            .then(response => {
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', 'selected_articles.csv');
                document.body.appendChild(link);
                link.click();
            })
            .catch(error => console.error('Error downloading CSV:', error));
    };

    const downloadTitles = () => {
        const titles = Array.isArray(selectedRows) ? selectedRows.map(article => article.page_title).join('\n') : '';
        const blob = new Blob([titles], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'selected_article_titles.txt');
        document.body.appendChild(link);
        link.click();
    };

    const metrics = [
        { key: 'pred_qual', label: 'Predicted Quality' },
        { key: 'num_refs', label: 'Number of References' },
        { key: 'num_media', label: 'Number of Media' },
        { key: 'num_wikilinks', label: 'Number of Wikilinks' },
        { key: 'num_categories', label: 'Number of Categories' },
        { key: 'num_headings', label: 'Number of Headings' },
        { key: 'page_length', label: 'Page Length' },
    ];

//     return (
//         <div className="selected-articles">
//             {selectedRows.length > 0 && (
//                 <div>
//                     <button onClick={downloadCSV} className="btn btn-primary">
//                         Download CSV
//                     </button>
//                     <button onClick={downloadTitles} className="btn btn-secondary">
//                         Download Titles
//                     </button>

//                     <div className="plot-container">
//                         {articleData.length > 0 && (
//                             metrics.map(metric => {
//                                 const isSingleAxisMetric = ['pred_qual', 'page_length'].includes(metric.key);  // Add metrics that should only have one axis
                                
//                                 return (
//                                     <div key={metric.key} className="plot-item">
//                                         <Plot
//                                             data={[
//                                                 {
//                                                     x: articleData.map(d => d.month),
//                                                     y: articleData.map(d => d[metric.key]),
//                                                     type: 'scatter',
//                                                     mode: 'lines',
//                                                     name: `Mean ${metric.label}`,
//                                                     yaxis: 'y1',
//                                                     line: { color: 'blue' } // Set line color to blue for Mean
//                                                 },
//                                                 // Conditionally render the "Sum" line only for non-single-axis metrics
//                                                 ...(!isSingleAxisMetric ? [{
//                                                     x: articleData.map(d => d.month),
//                                                     y: articleData.map(d => d[`${metric.key}_sum`]),
//                                                     type: 'scatter',
//                                                     mode: 'lines',
//                                                     name: `Sum ${metric.label}`,
//                                                     yaxis: 'y2',
//                                                     line: { color: 'blue' } // Set line color to blue for Sum
//                                                 }] : [])
//                                             ]}
//                                             layout={{
//                                                 title: `${metric.label} over Time`,
//                                                 xaxis: {
//                                                     rangeselector: {
//                                                         buttons: [
//                                                             { count: 6, label: '6M', step: 'month', stepmode: 'backward' },
//                                                             { count: 1, label: '1Y', step: 'year', stepmode: 'backward' },
//                                                             { count: 5, label: '5Y', step: 'year', stepmode: 'backward' },
//                                                             { step: 'all' }
//                                                         ]
//                                                     },
//                                                     rangeslider: { visible: true },
//                                                     type: 'date'
//                                                 },
//                                                 yaxis: { 
//                                                     title: `Mean ${metric.label}`, 
//                                                     side: 'left', 
//                                                     showgrid: false 
//                                                 },
//                                                 // Conditionally add the second y-axis for non-single-axis metrics
//                                                 ...(!isSingleAxisMetric ? {
//                                                     yaxis2: {
//                                                         title: `Sum ${metric.label}`,
//                                                         overlaying: 'y',
//                                                         side: 'right',
//                                                         showgrid: false,
//                                                     }
//                                                 } : {}),
//                                                 template: 'plotly_white',
//                                                 showlegend: false,
//                                                 hovermode: 'x unified'
//                                             }}
//                                             config={{ displayModeBar: false }}
//                                             useResizeHandler={true}
//                                             style={{ width: "100%", height: "400px" }}
//                                             hoverlabel={{
//                                                 bgcolor: "white",
//                                                 font: { size: 12 }
//                                             }}
//                                             hoverinfo="none"
//                                             hovertemplate={`Month: %{x}<br>Mean: %{y}<br>Sum: %{customdata}`}
//                                             customdata={articleData.map(d => d[`${metric.key}_sum`])}
//                                         />
//                                     </div>
//                                 );
//                         })
//                     )}
//     {pageViewsData.length > 0 && (
//         <div className="plot-item">
//             <Plot
//                 data={[
//                     {
//                         x: pageViewsData.map(d => d.month),
//                         y: pageViewsData.map(d => d.views),
//                         type: 'scatter',
//                         mode: 'lines',
//                         name: 'Page Views',
//                         line: { color: 'blue' }, // Set line color to blue for Page Views
//                         hovertemplate: `Month: %{x}<br>Page Views: %{y}<extra></extra>`
//                     }
//                 ]}
//                 layout={{
//                     title: `Page Views over Time`,
//                     xaxis: {
//                         rangeselector: {
//                             buttons: [
//                                 { count: 6, label: '6M', step: 'month', stepmode: 'backward' },
//                                 { count: 1, label: '1Y', step: 'year', stepmode: 'backward' },
//                                 { count: 5, label: '5Y', step: 'year', stepmode: 'backward' },
//                                 { step: 'all' }
//                             ]
//                         },
//                         rangeslider: { visible: true },
//                         type: 'date'
//                     },
//                     yaxis: { title: 'Mean Page Views' },
//                     template: 'plotly_white',
//                     showlegend: false
//                 }}
//                 config={{ displayModeBar: false }}
//                 useResizeHandler={true}
//                 style={{ width: "100%", height: "400px" }}
//             />
//         </div>
//     )}
// </div>


//                 </div>
//             )}
//             {selectedRows.length === 0 && (
//                 <p>No articles selected.</p>
//             )}
//         </div>
//     );


        return (
            <div className="selected-articles">
                {selectedRows.length > 0 && (
                    <div>
                        <button onClick={downloadCSV} className="btn btn-primary">
                            Download CSV
                        </button>
                        <button onClick={downloadTitles} className="btn btn-secondary">
                            Download Titles
                        </button>
                        <p style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>
                            Selected articles shown above. Correlations visible in the heatmap.
                        </p>
                    </div>
                )}
                {selectedRows.length === 0 && (
                    <p>No articles selected.</p>
                )}
            </div>
        );
    };

export default SelectedArticles;

