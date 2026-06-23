import { useEffect, useState } from 'react';
import Plot from '../Plot';
import axios from 'axios';

const quality_order = ['List', 'Stub', 'Start', 'C', 'B', 'GA', 'A', 'FL', 'FA'];
const importance_order = ['Unknown', 'Low', 'Mid', 'High', 'Top'];
const color_map_importance = {
    'Unknown': '#dcdcdc',
    'Low': '#ffd6ff',
    'Mid': '#ffc1ff',
    'High': '#ffacff',
    'Top': '#ff97ff'
};

const ImportanceQualityStackedBarChart = ({ project }) => {
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
            acc[`${quality}-${importance}`] = (acc[`${quality}-${importance}`] || 0) + 1;
            return acc;
        }, {});

        const stackedBarChartData = [];
        quality_order.forEach(quality => {
            importance_order.forEach(importance => {
                const count = groupedData[`${quality}-${importance}`] || 0;
                stackedBarChartData.push({
                    Quality: quality,
                    Importance: importance,
                    count: count
                });
            });
        });

        // Calculate total counts and percentages
        stackedBarChartData.forEach(item => {
            const totalCount = stackedBarChartData
                .filter(i => i.Quality === item.Quality)
                .reduce((sum, i) => sum + i.count, 0);
            item.total_count = totalCount;
            item.percentage = totalCount ? (item.count / totalCount) * 100 : 0;
        });

        setStackedData(stackedBarChartData);
    }, [data]);

    return (
        <div className="plot-container">
            <Plot
                data={importance_order.map(importance => ({
                    x: quality_order,
                    y: quality_order.map(quality => {
                        const item = stackedData.find(d => d.Quality === quality && d.Importance === importance);
                        return item ? item.percentage : 0;
                    }),
                    name: importance,
                    type: 'bar',
                    marker: {
                        color: color_map_importance[importance],
                        line: {
                            color: 'black',
                            width: 1
                        }
                    },
                    hoverinfo: 'x+name+text',
                    text: quality_order.map(quality => {
                        const item = stackedData.find(d => d.Quality === quality && d.Importance === importance);
                        return item ? `${importance}: ${item.count} (${item.percentage.toFixed(2)}%)` : '';
                    }),
                    textposition: 'none',
                }))}
                layout={{
                    title: 'Stacked Bar Chart by Quality and Importance Classes',
                    barmode: 'stack',
                    xaxis: {
                        categoryorder: 'array',
                        categoryarray: quality_order,
                        title: 'Quality'
                    },
                    yaxis: {
                        title: 'Percentage (%)',
                        showgrid: true,
                        gridcolor: 'lightgrey'
                    },
                    legend: { traceorder: 'reversed' },
                    plot_bgcolor: 'white',
                    paper_bgcolor: 'white',
                    annotations: quality_order.map(quality => {
                        const filteredData = stackedData.filter(item => item.Quality === quality);
                        if (filteredData.length > 0) {
                            const totalCount = filteredData[0].total_count;
                            return {
                                x: quality,
                                y: 100,
                                text: `Total: ${totalCount}`,
                                showarrow: false,
                                yshift: 10,
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

export default ImportanceQualityStackedBarChart;
