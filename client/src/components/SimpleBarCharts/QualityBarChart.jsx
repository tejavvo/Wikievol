import { useEffect, useState } from 'react';
import Plot from '../Plot';
import axios from 'axios';

const QualityBarChart = ({ project }) => {
    const [data, setData] = useState([]);
    const [qualityCounts, setQualityCounts] = useState([]);

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

        const quality_order = ['List', 'Stub', 'Start', 'C', 'B', "GA", 'A', 'FL', 'FA'];
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

        // Verify column names
        if (!('quality_class' in data[0])) {
            console.error('Column "quality_class" not found in data');
            return;
        }

        const filteredData = data.filter(item => !['Disambig', 'Redirect'].includes(item.quality_class));

        const qualityData = filteredData.reduce((acc, item) => {
            acc[item.quality_class] = (acc[item.quality_class] || 0) + 1;
            return acc;
        }, {});

        const qualityCounts = quality_order.map(quality => ({
            Quality: quality,
            Count: qualityData[quality] || 0,
            Color: color_map[quality]
        }));

        setQualityCounts(qualityCounts);
    }, [data]);

    return (
        <div className="plot-container">
            <Plot
                data={[
                    {
                        x: qualityCounts.map(item => item.Quality),
                        y: qualityCounts.map(item => item.Count),
                        type: 'bar',
                        marker: { color: qualityCounts.map(item => item.Color) },
                    }
                ]}
                layout={{
                    title: 'Number of Articles by Quality',
                    plot_bgcolor: 'white',
                    paper_bgcolor: 'white',
                    xaxis: { showgrid: true, gridcolor: 'lightgrey' },
                    yaxis: { showgrid: true, gridcolor: 'lightgrey' },
                    autosize: true,
                }}
                useResizeHandler={true}
                style={{ width: "100%", height: "100%" }}
            />
        </div>
    );
};

export default QualityBarChart;
