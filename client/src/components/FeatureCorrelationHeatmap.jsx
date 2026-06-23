import { useState, useEffect } from 'react';
import axios from 'axios';
import Plot from './Plot';

const FeatureCorrelationHeatmap = ({ project }) => {
    const [keys, setKeys] = useState([]);
    const [values, setValues] = useState([]);

    useEffect(() => {
        if (!project) return;
        axios.get(`/get_correlation?project=${project}`)
            .then(response => {
                // Backend returns the correlation matrix as a nested object:
                // { feature: { otherFeature: correlation, ... }, ... }
                const parsedData = response.data;
                if (!parsedData || !parsedData.pred_qual) {
                    console.error('Unexpected correlation response:', parsedData);
                    return;
                }

                const nextKeys = Object.keys(parsedData.pred_qual);
                const nextValues = nextKeys.map(key => parsedData.pred_qual[key]);

                if (nextValues.some(val => isNaN(val))) {
                    console.error('Correlation matrix contains NaN values:', nextValues);
                    return;
                }

                // Sort features by their correlation with pred_qual.
                const sorted = nextKeys
                    .map((key, index) => ({ key, value: nextValues[index] }))
                    .sort((a, b) => a.value - b.value);

                setKeys(sorted.map(item => item.key));
                setValues(sorted.map(item => item.value));
            })
            .catch(error => {
                console.error('Error fetching correlation data:', error);
            });
    }, [project]);

    if (keys.length === 0 || values.length === 0) {
        return <div>Loading…</div>;
    }

    const customColorscale = [
        [0, 'rgb(230, 245, 255)'],
        [1, 'rgb(8, 48, 107)']
    ];

    return (
        <div className="plot-container">
            <Plot
                data={[
                    {
                        z: [values],
                        x: keys,
                        y: ['pred_qual'],
                        type: 'heatmap',
                        colorscale: customColorscale,
                        showscale: true,
                        colorbar: {
                            title: 'Correlation',
                            titleside: 'right'
                        }
                    }
                ]}
                layout={{
                    title: 'Correlation of Features with pred_qual',
                    xaxis: {
                        automargin: true,
                        tickangle: -45,
                    },
                    yaxis: {
                        automargin: true,
                    },
                    height: 300,
                    plot_bgcolor: '#ffffff',
                    paper_bgcolor: '#ffffff',
                }}
                useResizeHandler={true}
                style={{ width: '100%', height: '100%' }}
            />
        </div>
    );
};

export default FeatureCorrelationHeatmap;
