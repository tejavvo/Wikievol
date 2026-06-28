import Plot from '../Plot';

const Graph = ({ data, metrics }) => {
    if (data.length === 0) return <div>Loading...</div>;

    const allGraphs = metrics.map((metric) => {
        const metricKeyMap = {
            pred_qual: { mean: 'mean_pred_qual', sum: 'mean_pred_qual' },
            num_refs: { mean: 'mean_refs', sum: 'sum_refs' },
            num_media: { mean: 'mean_media', sum: 'sum_media' },
            num_categories: { mean: 'mean_categories', sum: 'sum_categories' },
            num_wikilinks: { mean: 'mean_wikilinks', sum: 'sum_wikilinks' },
            num_headings: { mean: 'mean_headings', sum: 'sum_headings' },
            page_length: { mean: 'mean_page_length', sum: 'sum_page_length' },
        };

        const meanKey = metricKeyMap[metric]?.mean;
        const sumKey = metricKeyMap[metric]?.sum;

        const meanData = data.map(d => d[meanKey]);
        const sumData = data.map(d => d[sumKey]);
        const xData = data.map(d => d.month);

        // Determine if the metric should have only a single y-axis
        const isSingleAxisMetric = ['pred_qual', 'page_length', 'page_views'].includes(metric);

        // Plot both mean and sum with the same color and no legend
        const plotData = [
            {
                x: xData,
                y: meanData,
                type: 'scatter',
                mode: 'lines',
                name: `Mean ${metric.replace('_', ' ')}`,
                yaxis: 'y1',
                line: { color: 'blue' },  // Set line color to blue for Mean
                showlegend: false, // Hide the legend
                hovertemplate: `%{y}`,
            },
            // Conditionally render the "Sum" line only for non-single-axis metrics
            ...(!isSingleAxisMetric ? [{
                x: xData,
                y: sumData,
                type: 'scatter',
                mode: 'lines',
                name: `Sum ${metric.replace('_', ' ')}`,
                yaxis: 'y2',
                line: { color: 'blue' },  // Set line color to blue for Sum
                showlegend: false, // Hide the legend
                hovertemplate: `%{y}`,
            }] : [])
        ];

        return (
            <div key={metric} style={{ width: '100%', marginTop: '20px' }}>
                <Plot
                    data={plotData}
                    layout={{
                        title: `Mean and Sum of ${metric.replace('_', ' ')} over Time`,
                        xaxis: {
                            rangeselector: {
                                buttons: [
                                    { count: 6, label: '6M', step: 'month', stepmode: 'backward' },
                                    { count: 1, label: '1Y', step: 'year', stepmode: 'backward' },
                                    { count: 5, label: '5Y', step: 'year', stepmode: 'backward' },
                                    { step: 'all' }
                                ]
                            },
                            rangeslider: { visible: true },
                            type: 'date'
                        },
                        yaxis: {
                            title: `Mean ${metric.replace('_', ' ')}`,
                            side: 'left',
                            rangemode: 'tozero'
                        },
                        // Conditionally add the second y-axis for non-single-axis metrics
                        ...(!isSingleAxisMetric ? {
                            yaxis2: {
                                title: `Sum ${metric.replace('_', ' ')}`,
                                overlaying: 'y',
                                side: 'right',
                                rangemode: 'tozero'
                            }
                        } : {}),
                        template: 'plotly_white',
                        showlegend: false,
                        hovermode: 'x unified' // Ensure both traces' hover labels appear together
                    }}
                    config={{ displayModeBar: false }}
                    useResizeHandler={true}
                    style={{ width: "100%", height: "100%" }}
                />
            </div>
        );
    });

    return (
        <div>
            {allGraphs}
        </div>
    );
};

export default Graph;
