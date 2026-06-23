import { useState, useEffect } from 'react';
import axios from 'axios';
import SelectedArticles from './SelectedArticles';
import DataTable from 'react-data-table-component';

const FilterTable = ({ project }) => {
    const [filters, setFilters] = useState({
        num_refs_min: '',
        num_refs_max: '',
        num_media_min: '',
        num_media_max: '',
        num_wikilinks_min: '',
        num_wikilinks_max: '',
        num_categories_min: '',
        num_categories_max: '',
        num_headings_min: '',
        num_headings_max: '',
        page_length_min: '',
        page_length_max: '',
        pred_qual_min: '',
        pred_qual_max: '',
        quality_class: [],
        importance_class: []
    });

    const [tableData, setTableData] = useState([]);
    const [selectedRows, setSelectedRows] = useState([]); // Reset to an empty array

    useEffect(() => {
        if (!project) return;
        // Fetch min/max values to set placeholders
        axios.get(`/minmax?project=${project}`)
            .then(response => {
                const data = response.data;
                setFilters(prevFilters => ({
                    ...prevFilters,
                    num_refs_min: data.num_refs[0],
                    num_refs_max: data.num_refs[1],
                    num_media_min: data.num_media[0],
                    num_media_max: data.num_media[1],
                    num_wikilinks_min: data.num_wikilinks[0],
                    num_wikilinks_max: data.num_wikilinks[1],
                    num_categories_min: data.num_categories[0],
                    num_categories_max: data.num_categories[1],
                    num_headings_min: data.num_headings[0],
                    num_headings_max: data.num_headings[1],
                    page_length_min: data.page_length[0],
                    page_length_max: data.page_length[1],
                    pred_qual_min: data.pred_qual[0],
                    pred_qual_max: data.pred_qual[1],
                }));
            })
            .catch(error => console.error('Error fetching min/max values:', error));
        
        // Fetch complete data initially
        axios.get(`/get_csv_data?project=${project}`)
            .then(response => {
                setTableData(response.data);
            })
            .catch(error => console.error('Error fetching data:', error));
    }, [project]);

    const handleInputChange = (event) => {
        const { name, value } = event.target;
        setFilters(prevFilters => ({
            ...prevFilters,
            [name]: value
        }));
    };

    const handleCheckboxChange = (event) => {
        const { name, value, checked } = event.target;
        setFilters(prevFilters => {
            const updatedArray = checked 
                ? [...prevFilters[name], value] 
                : prevFilters[name].filter(item => item !== value);
            return {
                ...prevFilters,
                [name]: updatedArray
            };
        });
    };

    const convertToNumber = (value) => {
        const number = parseFloat(value);
        return isNaN(number) ? undefined : number;
    };

    const filterData = () => {
        // Reset selected rows
        setSelectedRows([]);

        // Convert numeric filter values to numbers
        const numericFilters = {
            num_refs_min: convertToNumber(filters.num_refs_min),
            num_refs_max: convertToNumber(filters.num_refs_max),
            num_media_min: convertToNumber(filters.num_media_min),
            num_media_max: convertToNumber(filters.num_media_max),
            num_wikilinks_min: convertToNumber(filters.num_wikilinks_min),
            num_wikilinks_max: convertToNumber(filters.num_wikilinks_max),
            num_categories_min: convertToNumber(filters.num_categories_min),
            num_categories_max: convertToNumber(filters.num_categories_max),
            num_headings_min: convertToNumber(filters.num_headings_min),
            num_headings_max: convertToNumber(filters.num_headings_max),
            page_length_min: convertToNumber(filters.page_length_min),
            page_length_max: convertToNumber(filters.page_length_max),
            pred_qual_min: convertToNumber(filters.pred_qual_min),
            pred_qual_max: convertToNumber(filters.pred_qual_max),
            quality_class: filters.quality_class,
            importance_class: filters.importance_class
        };

        axios.post(`/filter?project=${project}`, numericFilters)
            .then(response => {
                setTableData(response.data);
            })
            .catch(error => console.error('Error filtering data:', error));
    };
    const columns = [
        {
            name: 'Page Title',
            selector: row => row.page_title,
            sortable: true,
            cell: row => <a href={`https://en.wikipedia.org/w/index.php?oldid=${row.revision_id}`} target="_blank" rel="noopener noreferrer">{row.page_title}</a>
        },
        {
            name: 'Number of References',
            selector: row => row.num_refs,
            sortable: true,
        },
        {
            name: 'Number of Wikilinks',
            selector: row => row.num_wikilinks,
            sortable: true,
        },
        {
            name: 'Number of Media',
            selector: row => row.num_media,
            sortable: true,
        },
        {
            name: 'Number of Categories',
            selector: row => row.num_categories,
            sortable: true,
        },
        {
            name: 'Number of Headings',
            selector: row => row.num_headings,
            sortable: true,
        },
        {
            name: 'Page Length',
            selector: row => row.page_length,
            sortable: true,
        },
        {
            name: 'Predicted Quality',
            selector: row => row.pred_qual ? row.pred_qual.toFixed(3) : '-',
            sortable: true,
        },
        {
            name: 'Revision ID',
            selector: row => row.revision_id,
            sortable: true,
        },
        {
            name: 'Quality Class',
            selector: row => row.quality_class,
            sortable: true,
        },
        {
            name: 'Importance Class',
            selector: row => row.importance_class,
            sortable: true,
        },
    ];

    const handleSelectedRowsChange = (state) => {
        setSelectedRows(state.selectedRows);
    };

    return (
        <div className="main-container">
            <section>
                <h1 className="sub-section-text">Filter Data</h1>
                <form id="filter-form" className="form">
                    <div className="form-row">
                        <div className="form-group">
                            <label htmlFor="num_refs">Number of References:</label>
                            <input
                                type="number"
                                id="num_refs_min"
                                name="num_refs_min"
                                value={filters.num_refs_min}
                                onChange={handleInputChange}
                                placeholder="Min"
                            />
                            <input
                                type="number"
                                id="num_refs_max"
                                name="num_refs_max"
                                value={filters.num_refs_max}
                                onChange={handleInputChange}
                                placeholder="Max"
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="num_media">Number of Media:</label>
                            <input
                                type="number"
                                id="num_media_min"
                                name="num_media_min"
                                value={filters.num_media_min}
                                onChange={handleInputChange}
                                placeholder="Min"
                            />
                            <input
                                type="number"
                                id="num_media_max"
                                name="num_media_max"
                                value={filters.num_media_max}
                                onChange={handleInputChange}
                                placeholder="Max"
                            />
                        </div>
                    </div>
                    <div className="form-row">
                        <div className="form-group">
                            <label htmlFor="num_categories">Number of Categories:</label>
                            <input
                                type="number"
                                id="num_categories_min"
                                name="num_categories_min"
                                value={filters.num_categories_min}
                                onChange={handleInputChange}
                                placeholder="Min"
                            />
                            <input
                                type="number"
                                id="num_categories_max"
                                name="num_categories_max"
                                value={filters.num_categories_max}
                                onChange={handleInputChange}
                                placeholder="Max"
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="num_wikilinks">Number of Wikilinks:</label>
                            <input
                                type="number"
                                id="num_wikilinks_min"
                                name="num_wikilinks_min"
                                value={filters.num_wikilinks_min}
                                onChange={handleInputChange}
                                placeholder="Min"
                            />
                            <input
                                type="number"
                                id="num_wikilinks_max"
                                name="num_wikilinks_max"
                                value={filters.num_wikilinks_max}
                                onChange={handleInputChange}
                                placeholder="Max"
                            />
                        </div>
                    </div>
                    <div className="form-row">
                        <div className="form-group">
                            <label htmlFor="num_headings">Number of Headings:</label>
                            <input
                                type="number"
                                id="num_headings_min"
                                name="num_headings_min"
                                value={filters.num_headings_min}
                                onChange={handleInputChange}
                                placeholder="Min"
                            />
                            <input
                                type="number"
                                id="num_headings_max"
                                name="num_headings_max"
                                value={filters.num_headings_max}
                                onChange={handleInputChange}
                                placeholder="Max"
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="page_length">Page Length:</label>
                            <input
                                type="number"
                                id="page_length_min"
                                name="page_length_min"
                                value={filters.page_length_min}
                                onChange={handleInputChange}
                                placeholder="Min"
                            />
                            <input
                                type="number"
                                id="page_length_max"
                                name="page_length_max"
                                value={filters.page_length_max}
                                onChange={handleInputChange}
                                placeholder="Max"
                            />
                        </div>
                    </div>
                    <div className="form-row">
                        <div className="form-group">
                            <label htmlFor="pred_qual">Predicted Quality:</label>
                            <input
                                type="number"
                                id="pred_qual_min"
                                name="pred_qual_min"
                                value={filters.pred_qual_min}
                                onChange={handleInputChange}
                                placeholder="Min"
                            />
                            <input
                                type="number"
                                id="pred_qual_max"
                                name="pred_qual_max"
                                value={filters.pred_qual_max}
                                onChange={handleInputChange}
                                placeholder="Max"
                            />
                        </div>
                    </div>
                    <div className="form-row">
                        <div className="form-group">
                            <label htmlFor="quality_class">Quality Class:</label>
                            <div className="checkbox-group">
                                <label>
                                    <input
                                        type="checkbox"
                                        name="quality_class"
                                        value="All"
                                        onChange={handleCheckboxChange}
                                    /> All
                                </label>
                                <label>
                                    <input
                                        type="checkbox"
                                        name="quality_class"
                                        value="Start"
                                        onChange={handleCheckboxChange}
                                    /> Start
                                </label>
                                <label>
                                    <input
                                        type="checkbox"
                                        name="quality_class"
                                        value="C"
                                        onChange={handleCheckboxChange}
                                    /> C
                                </label>
                                <label>
                                    <input
                                        type="checkbox"
                                        name="quality_class"
                                        value="B"
                                        onChange={handleCheckboxChange}
                                    /> B
                                </label>
                                <label>
                                    <input
                                        type="checkbox"
                                        name="quality_class"
                                        value="GA"
                                        onChange={handleCheckboxChange}
                                    /> GA
                                </label>
                                <label>
                                    <input
                                        type="checkbox"
                                        name="quality_class"
                                        value="FA"
                                        onChange={handleCheckboxChange}
                                    /> FA
                                </label>
                            </div>
                        </div>
                        <div className="form-group">
                            <label htmlFor="importance_class">Importance Class:</label>
                            <div className="checkbox-group">
                                <label>
                                    <input
                                        type="checkbox"
                                        name="importance_class"
                                        value="Low"
                                        onChange={handleCheckboxChange}
                                    /> Low
                                </label>
                                <label>
                                    <input
                                        type="checkbox"
                                        name="importance_class"
                                        value="Mid"
                                        onChange={handleCheckboxChange}
                                    /> Mid
                                </label>
                                <label>
                                    <input
                                        type="checkbox"
                                        name="importance_class"
                                        value="High"
                                        onChange={handleCheckboxChange}
                                    /> High
                                </label>
                                <label>
                                    <input
                                        type="checkbox"
                                        name="importance_class"
                                        value="All"
                                        onChange={handleCheckboxChange}
                                    /> All
                                </label>
                            </div>
                        </div>
                    </div>
                    <button type="button" className="btn btn-primary" onClick={filterData}>Filter</button>
                </form>
                {/* <div className="margin-top-3 scrollable-table-container">
                    <DataTable
                        columns={columns}
                        data={tableData}
                        selectableRows
                        onSelectedRowsChange={handleSelectedRowsChange}
                        pagination
                        highlightOnHover
                        pointerOnHover
                        selectableRowsComponentProps={{ inkdisabled: "true" }}
                    />
                </div> */}

                <div className="margin-top-3 scrollable-table-container">
                    <div className="scroll-hint">
                        <span>Scroll for more columns</span>
                    </div>
                    <div className="scroll-indicator">
                        <i className="fa fa-arrow-right"></i>
                    </div>
                    <DataTable
                        columns={columns}
                        data={tableData}
                        selectableRows
                        onSelectedRowsChange={handleSelectedRowsChange}
                        pagination
                        highlightOnHover
                        pointerOnHover
                        selectableRowsComponentProps={{ inkdisabled: "true" }}
                    />
                </div>


                <SelectedArticles selectedRows={selectedRows} project={project} key={tableData.length} />
            </section>
        </div>
    );
};

export default FilterTable;
