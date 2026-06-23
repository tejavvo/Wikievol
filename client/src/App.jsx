import { useState, lazy, Suspense } from 'react';
import Header from './components/Header';
import Footer from './components/Footer';
import WikiProjectDropdown from './components/WikiProjectDropdown';
import './App.css';
import axios from 'axios';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';

// The chart components pull in plotly (a large library). Load them lazily so
// the initial page — just the WikiProject dropdown — stays small and fast;
// plotly is only fetched once a project is selected.
const FilterTable = lazy(() => import('./components/FilterData/FilterTable'));
const QualityImportanceStackedBarChart = lazy(() => import('./components/SimpleBarCharts/QualityImportanceStackedBarChart'));
const ImportanceQualityStackedBarChart = lazy(() => import('./components/SimpleBarCharts/ImportanceQualityStackedBarChart'));
const FeatureCorrelationHeatmap = lazy(() => import('./components/FeatureCorrelationHeatmap'));
const Graph = lazy(() => import('./components/AverageOfFeatures/Graph'));

const App = () => {
  const [selectedProject, setSelectedProject] = useState('');
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const metrics = [
    'pred_qual',
    'num_refs',
    'num_media',
    'num_categories',
    'num_wikilinks',
    'num_headings',
    'page_length'
  ];

  const handleProjectSelect = (project) => {
    setSelectedProject(project);
    fetchData(project);
  };

  const fetchData = (project) => {
    setLoading(true);
    setError(null);
    setData([]);
    axios.get(`/get_csv_data_monthly_aggregated?project=${project}`)
      .then(response => {
        setData(response.data);
      })
      .catch(err => {
        console.error('Error fetching data:', err);
        setError('Could not load data for this WikiProject. Please try again.');
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="main-container">
      <Header />
      <section>
        <div className='margin-top-3'>
          <WikiProjectDropdown onSelectProject={handleProjectSelect} />
        </div>

        {loading && <p className="margin-top-3">Loading data…</p>}
        {error && <p className="margin-top-3" style={{ color: '#c0392b' }}>{error}</p>}

        {selectedProject && !error && (
          <>
            <div className="section-text margin-top-3">
              <a
                href={`https://en.wikipedia.org/wiki/Wikipedia:WikiProject_${selectedProject}`}
                target="_blank"
                rel="noopener noreferrer"
                className="title-link"
              >
                {`Wikipedia:WikiProject ${selectedProject}`}
              </a>
            </div>

            <Suspense fallback={<p className="margin-top-3">Loading charts…</p>}>
              <Tabs className="margin-top-3">
                <TabList>
                  <Tab>Wikiproject Overview</Tab>
                  <Tab>Drill Down</Tab>
                </TabList>

                <TabPanel>
                  <div className="margin-top-3">
                    <QualityImportanceStackedBarChart project={selectedProject} />
                  </div>
                  <div className="margin-top-3">
                    <ImportanceQualityStackedBarChart project={selectedProject} />
                  </div>
                  <div className="margin-top-3">
                    <Graph data={data} metrics={metrics} />
                  </div>
                </TabPanel>

                <TabPanel>
                  <div className="margin-top-3">
                    <FilterTable project={selectedProject} />
                  </div>
                  <div className="margin-top-3">
                    <FeatureCorrelationHeatmap project={selectedProject} />
                  </div>
                </TabPanel>
              </Tabs>
            </Suspense>
          </>
        )}
      </section>
      <Footer />
    </div>
  );
};

export default App;
