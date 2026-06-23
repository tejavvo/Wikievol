import { useEffect, useState } from 'react';
import Plot from '../Plot';
import axios from 'axios';

const quality_order = ['List', 'Stub', 'Start', 'C', 'B', 'GA', 'A', 'FL', 'FA'];
const importance_order = ['Unknown', 'Low', 'Mid', 'High', 'Top'];
const color_map = {
    'List': '#c7b1ff',
    'Stub': '#ffa4a4',
    'Start': '#ffaa66',
    'C': '#ffff66',
    'B': '#b2ff66',
    'GA': '#66ff66',
    'A': '#66ffff',
    'FL': '#9cbdff',
    'FA': '#9cbdff'
};

const QualityImportanceStackedBarChart = ({ project }) => {
    const [data, setData] = useState([]);
    const [stackedData, setStackedData] = useState([]);

    useEffect(() => {
        if (!project) return;
        axios.get(`/get_csv_data?project=${project}`)
            .then(response => {
                setData(response.data);
            })
            .catch(error => console.error('Error fetching data:', error));
    }, [project]);

    useEffect(() => {
        if (data.length === 0) return;

        const filteredData = data.filter(item => item.quality_class && item.importance_class && !['Disambig', 'Redirect'].includes(item.quality_class));

        const groupedData = filteredData.reduce((acc, item) => {
            const quality = item.quality_class;
            const importance = item.importance_class;
            acc[`${importance}-${quality}`] = (acc[`${importance}-${quality}`] || 0) + 1;
            return acc;
        }, {});

        const stackedBarChartData = [];
        importance_order.forEach(importance => {
            quality_order.forEach(quality => {
                const count = groupedData[`${importance}-${quality}`] || 0;
                stackedBarChartData.push({
                    Importance: importance,
                    Quality: quality,
                    count: count
                });
            });
        });

        // Calculate total counts and percentages
        stackedBarChartData.forEach(item => {
            const totalCount = stackedBarChartData
                .filter(i => i.Importance === item.Importance)
                .reduce((sum, i) => sum + i.count, 0);
            item.total_count = totalCount;
            item.percentage = totalCount ? (item.count / totalCount) * 100 : 0;
        });

        setStackedData(stackedBarChartData);
    }, [data]);

    return (
        <div className="plot-container">
            <Plot
                data={quality_order.map(quality => ({
                    x: importance_order,
                    y: importance_order.map(importance => {
                        const item = stackedData.find(d => d.Importance === importance && d.Quality === quality);
                        return item ? item.percentage : 0;
                    }),
                    name: quality,
                    type: 'bar',
                    marker: {
                        color: color_map[quality],
                        line: {
                            color: 'black',
                            width: 1
                        }
                    },
                    hoverinfo: 'x+name+text',
                    text: importance_order.map(importance => {
                        const item = stackedData.find(d => d.Importance === importance && d.Quality === quality);
                        return item ? `${quality}: ${item.count} (${item.percentage.toFixed(2)}%)` : '';
                    }),
                    textposition: 'none',
                }))}
                layout={{
                    title: 'Stacked Bar Chart by Importance and Quality Classes',
                    barmode: 'stack',
                    xaxis: {
                        categoryorder: 'array',
                        categoryarray: importance_order,
                        title: 'Importance'
                    },
                    yaxis: {
                        title: 'Percentage (%)',
                        showgrid: true,
                        gridcolor: 'lightgrey'
                    },
                    legend: { traceorder: 'reversed' },
                    plot_bgcolor: 'white',
                    paper_bgcolor: 'white',
                    annotations: importance_order.map(importance => {
                        const filteredData = stackedData.filter(item => item.Importance === importance);
                        if (filteredData.length > 0) {
                            const totalCount = filteredData[0].total_count;
                            return {
                                x: importance,
                                y: 105,
                                text: `Total: ${totalCount}`,
                                showarrow: false,
                                yshift: 0,
                                xanchor: 'center',
                                font: {
                                    size: 12,
                                    color: 'black'
                                },
                                bgcolor: 'rgba(255, 255, 255, 0.7)',
                                bordercolor: 'black',
                                borderwidth: 1
                            };
                        }
                        return null;
                    }).filter(annotation => annotation !== null)
                }}
                config={{ displayModeBar: false }}
                useResizeHandler={true}
                style={{ width: "100%", height: "100%" }}
            />
        </div>
    );
};

export default QualityImportanceStackedBarChart;
