from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from .tools.throttled_brave_tool import ThrottledBraveSearchTool
from pydantic import BaseModel, Field
from typing import List
from .tools.push_tool import MailJetNotificationTool
from .model_client import create_llm, opencode_go_tools_enabled, using_opencode_go

OUTPUT_DIR = Path("src/stock_picker/output")

class TrendingCompany(BaseModel):
    """ A company that is in the news and attracting attention """
    name: str = Field(description="Company name")
    ticker: str = Field(description="Stock ticker symbol")
    reason: str = Field(description="Reason this company is trending in the news")

class TrendingCompanyList(BaseModel):
    """ List of multiple trending companies that are in the news """
    companies: List[TrendingCompany] = Field(description="List of companies trending in the news")

class TrendingCompanyResearch(BaseModel):
    """ Detailed research on a company """
    name: str = Field(description="Company name")
    market_position: str = Field(description="Current market position and competitive analysis")
    future_outlook: str = Field(description="Future outlook and growth prospects")
    investment_potential: str = Field(description="Investment potential and suitability for investment")

class TrendingCompanyResearchList(BaseModel):
    """ A list of detailed research on all the companies """
    research_list: List[TrendingCompanyResearch] = Field(description="Comprehensive research on all trending companies")


@CrewBase
class StockPicker():
    """StockPicker crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def trending_company_finder(self) -> Agent:
        return Agent(config=self.agents_config['trending_company_finder'],
                     tools=self._search_tools(), llm=create_llm(), memory=True)
    
    @agent
    def financial_researcher(self) -> Agent:
        return Agent(config=self.agents_config['financial_researcher'], llm=create_llm())

    @agent
    def stock_picker(self) -> Agent:
        return Agent(config=self.agents_config['stock_picker'], llm=create_llm(), memory=True)

    @agent
    def email_sender(self) -> Agent:
        return Agent(config=self.agents_config['email_sender'],
                     tools=[MailJetNotificationTool()], llm=create_llm(), memory=True)

    def _search_tools(self):
        if using_opencode_go() and not opencode_go_tools_enabled():
            return []
        return [ThrottledBraveSearchTool()]

    def _task_config(self, task_name):
        config = dict(self.tasks_config[task_name])
        output_file = config.get("output_file")
        if output_file:
            config["output_file"] = str(OUTPUT_DIR / Path(output_file).name)
        return config
    
    @task
    def find_trending_companies(self) -> Task:
        return Task(
            config=self._task_config('find_trending_companies'),
            output_pydantic=TrendingCompanyList,
        )

    @task
    def research_trending_companies(self) -> Task:
        return Task(
            config=self._task_config('research_trending_companies'),
            output_pydantic=TrendingCompanyResearchList,
        )

    @task
    def pick_best_company(self) -> Task:
        return Task(
            config=self._task_config('pick_best_company'),
        )

    @task
    def email_sender_task(self) -> Task:
        return Task(
            config=self._task_config('send_email_task'),
        )

    @crew
    def crew(self) -> Crew:
        """Creates the StockPicker crew"""
            
        return Crew(
            agents=[
                self.trending_company_finder(),
                self.financial_researcher(),
                self.stock_picker(),
                self.email_sender(),
            ],
            tasks=[
                self.find_trending_companies(),
                self.research_trending_companies(),
                self.pick_best_company(),
                self.email_sender_task(),
            ],
            process=Process.sequential,
            verbose=True,
        )
