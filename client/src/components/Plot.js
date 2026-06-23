// Shared Plotly component.
//
// The default `react-plotly.js` import bundles the full plotly.js (~3.5 MB).
// The dashboard only uses cartesian traces (bar, scatter, heatmap), so we build
// the React component from the much smaller `plotly.js-cartesian-dist-min`
// bundle via the factory. This cuts the production bundle dramatically.
//
// NOTE: if a future chart needs a non-cartesian trace (e.g. `scatterpolar` for a
// radar chart, or `pie`), switch this import to a bundle that includes it, or
// register the extra trace module here.
import createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-cartesian-dist-min';

const Plot = createPlotlyComponent(Plotly);

export default Plot;
