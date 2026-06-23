import { useState, useEffect } from 'react';
import Select from 'react-select';
import axios from 'axios';

const WikiProjectDropdown = ({ onSelectProject }) => {
  const [wikiprojects, setWikiProjects] = useState([]);

  useEffect(() => {
    axios.get('/get_wikiprojects')
      .then(response => {
        setWikiProjects(response.data.map(name => ({ label: name, value: name })));
      })
      .catch(error => {
        console.error('Error fetching WikiProjects:', error);
      });
  }, []);

  const handleProjectSelect = (option) => {
    axios.post('/set_selected_wikiproject', { project_name: option.value })
      .then(response => {
        console.log('WikiProject selected successfully:', response.data);
        onSelectProject(option.value); // You may still want to do something with the selected project.
      })
      .catch(error => {
        console.error('Error selecting WikiProject:', error);
      });
};



  return (
    <Select
      options={wikiprojects}
      onChange={(option) => {
        onSelectProject(option.value);
        handleProjectSelect(option);
      }}
      placeholder="Select a WikiProject"
      noOptionsMessage={() => 'No WikiProjects found'}
      styles={{
        control: (provided) => ({
          ...provided,
          minWidth: 240,
          margin: '0 auto',
          border: '1px solid #ced4da',
          boxShadow: 'none',
          '&:hover': {
            borderColor: '#ced4da',
          },
        }),
        menu: (provided) => ({
          ...provided,
          zIndex: 9999,
        }),
        option: (provided) => ({
          ...provided,
          textAlign: 'left',
        }),
        singleValue: (provided) => ({
          ...provided,
          textAlign: 'left',
        }),
      }}
      theme={(theme) => ({
        ...theme,
        colors: {
          ...theme.colors,
          primary25: '#f0f0f0',
          primary: '#007bff',
        },
      })}
      filterOption={(option, inputValue) => 
        option.label.toLowerCase().includes(inputValue.toLowerCase())
      }
    />
  );
};

export default WikiProjectDropdown;
