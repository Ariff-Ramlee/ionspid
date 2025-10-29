import { createContext, useContext, useState } from "react";

const ProgressContext = createContext();

export const ProgressProvider = ({ children }) => {
  const [uploaded, setUploaded] = useState(false);
  const [analysisDone, setAnalysisDone] = useState(false);

  return (
    <ProgressContext.Provider value={{ uploaded, setUploaded, analysisDone, setAnalysisDone }}>
      {children}
    </ProgressContext.Provider>
  );
};

export const useProgress = () => useContext(ProgressContext);
