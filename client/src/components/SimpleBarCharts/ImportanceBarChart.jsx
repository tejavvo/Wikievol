import { useEffect, useState } from 'react';
import Plot from '../Plot';
import axios from 'axios';

const ImportanceBarChart = ({ project }) => {
    const [data, setData] = useState([]);
    const [importanceCounts, setImportanceCounts] = useState([]);

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

        const importance_order = ['Unknown', 'Low', 'Mid', 'High', 'Top'];
        const color_map_importance = {
            'Unknown': '#dcdcdc',
            'Low': '#ffd6ff',
            'Mid': '#ffc1ff',
            'High': '#ffacff',
            'Top': '#ff97ff'
        };

        // Verify column names
        if (!('importance_class' in data[0])) {
            console.error('Column "importance_class" not found in data');
            return;
        }

        const importanceData = data.reduce((acc, item) => {
            acc[item.importance_class] = (acc[item.importance_class] || 0) + 1;
            return acc;
        }, {});

        const importanceCounts = importance_order.map(importance => ({
            Importance: importance,
            Count: importanceData[importance] || 0,
            Color: color_map_importance[importance]
        }));

        setImportanceCounts(importanceCounts);
    }, [data]);

    return (
        <div className="plot-container">
            <Plot
                data={[
                    {
                        x: importanceCounts.map(item => item.Importance),
                        y: importanceCounts.map(item => item.Count),
                        type: 'bar',
                        marker: { color: importanceCounts.map(item => item.Color) },
                    }
                ]}
                layout={{
                    title: 'Number of Articles by Importance',
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

export default ImportanceBarChart;
